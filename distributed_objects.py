# coding=utf-8
"""Contains the metaclass and basic DistributedObject from which all game
objects would inherit.
"""

import json
from uuid import uuid4


class Field:
    def __init__(self, property_type):
        self.t = property_type


class DistributedObjectMetaclass(type):
    """Scan the class for Fields and track those values meticulously."""
    def __new__(mcs, classname, baseclasses, attrs):
        # TODO: Why not put saved data in __dict__?
        attrs['_saved_field_data'] = {}  # This is where synced data go
        attrs['_dirty_field_data'] = {}  # This is where local changes go
        for name, thing in list(attrs.items()):
            # only override functionality for "DistributedField" objects
            # TODO: And methods decorated with @distributed?
            if not isinstance(thing, Field):
                continue

            # initialize the data in a type-specific way
            attrs['_dirty_field_data'][name] = {
                int: 0,
                float: 0.0,
                str: "",
                bytes: b"",
                bool: False,
                # TODO: UUID?
                # TODO: Datetime?
                # TODO: Keyframe (Datetime, Value) field?
            }.get(thing.t, None)

            # Create properties only for the specified fields.
            # We don't want to override global get/set behavior.
            def make_getter(n):
                def getter(self):
                    # Try to get from dirty, otherwise get from saved.
                    try:
                        return self._dirty_field_data[n]
                    except KeyError:
                        return self._saved_field_data[n]
                getter.__name__ = n
                return getter

            def make_setter(n):
                def setter(self, value):
                    # TODO: run validators here (enforce types, etc.)
                    self._dirty_field_data[n] = value
                setter.__name__ = n
                return setter

            attrs[name] = property(
                fget=make_getter(name), fset=make_setter(name),
                fdel=None, doc=name
                # TODO: Use the "help" param on the field for doc
            )

        return super().__new__(mcs, classname, baseclasses, attrs)


class DistributedObject(metaclass=DistributedObjectMetaclass):
    """A very simple implementation of the DistributedObjectMetaclass."""
    # Required attributes
    id = Field(str)
    owner = Field(str)  # Null means owned by the ZoneServer
    zone = Field(str)  # The id of the zone this DO belongs to.

    def __init__(self, *, zone=None, **kwargs):
        super().__init__()
        # Set the deleted flag
        self._deleted = False

        # Copy so they're not shared between all instances
        self._dirty_field_data = self._dirty_field_data.copy()
        self._saved_field_data = self._saved_field_data.copy()

        # Populate initial state from the kwargs
        self._dirty_field_data.update(zone=zone, **kwargs)

        # We must have an id. If it wasn't specified, UUID it.
        self.id = kwargs.get('id', str(uuid4()))

        # Must also have a zone. But we can't generate this one.
        assert self.zone, "DO must have a zone."

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.id)

    @property
    def created(self) -> bool:
        # This is only new is saved fields are not yet initialized
        return bool(self._saved_field_data)

    def _update(self, data: dict) -> None:
        # TODO: Nuke any keys in the dirty data that exist here?
        self._saved_field_data.update(data)

    def _delete(self) -> None:
        self._deleted = True

    def _save(self) -> None:
        self._saved_field_data.update(self._dirty_field_data)
        self._dirty_field_data.clear()

    def serialize(self, for_create=False) -> str:
        if for_create:
            # Just send everything if we're creating this
            return json.dumps(self._saved_field_data)

        # Always serialize id and zone, even if not dirty
        self._dirty_field_data.update(id=self.id, zone=self.zone)
        return json.dumps(self._dirty_field_data)


class DistributedObjectClassRegistry:
    def __init__(self, *args):
        # Validate these are actually DO subclasses
        if any(not issubclass(_, DistributedObject) for _ in args):
            raise TypeError("Only DistributedObject subclasses allowed.")

        # Save them to the classes  TODO: Why not a dict?
        self._classes = args

    def __getitem__(self, classname: str):
        """Provide index access for class retrieval."""
        for i in self._classes:
            if i.__name__ == classname:
                return i
        raise IndexError(
            "{} is not a registered Distributed Object.".format(classname))


class DistributedObjectState:
    """Persists the object state on the zone server and the client."""

    # TODO: Extend this with nice filtering for easier development.
    # For example: self.objects.filter(class=Message)
    def __init__(self, create_callback, update_callback, delete_callback):
        self._instances = []
        self.create_callback = create_callback
        self.update_callback = update_callback
        self.delete_callback = delete_callback

    def create(self, obj: DistributedObject):
        # TODO: Should the actual packet parsing happen here too?
        # If the object already exists, just update it
        to_update = self.get(obj.id)
        if to_update:
            to_update._update(obj._dirty_field_data)
            return

        self._instances.append(obj)
        self.create_callback(obj)
        obj._save()

    def update(self, **fields: dict):
        # TODO: What if the object doesn't exist? Any reason why this and
        # TODO: create can't be merged? They will still make the create/update
        # TODO: callbacks contextually
        obj_id = fields['id']  # ID is always serialized
        obj = self[obj_id]
        obj._update(fields)
        self.update_callback(obj)

    def delete(self, obj_id: str):
        obj = self[obj_id]
        self._instances.remove(obj)
        self.delete_callback(obj)

    def get(self, object_id, default=None):
        try:
            return self[object_id]
        except IndexError:
            return default

    def __getitem__(self, object_id: str):
        for o in self._instances:
            if o.id == object_id:
                return o
        raise IndexError(
            "{} ".format(object_id))

    def __len__(self):
        return len(self._instances)

    def __iter__(self):
        return iter(self._instances)