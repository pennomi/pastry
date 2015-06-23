import json
from uuid import uuid4


class Field:
    def __init__(self, property_type):
        self.t = property_type


class DistributedObjectMetaclass(type):
    def __new__(mcs, classname, baseclasses, attrs):
        attrs['_saved_field_data'] = {}  # This is where synced data go
        attrs['_dirty_field_data'] = {}  # This is where local changes go
        for name, thing in list(attrs.items()):
            # only override functionality for "DistributedField" objects
            # TODO: And methods decorated with @distributed?
            if not isinstance(thing, Field):
                continue

            # initialize the data in a type-specific way
            if thing.t == int:
                attrs['_saved_field_data'][name] = 0
            elif thing.t == float:
                attrs['_saved_field_data'][name] = 0.0
            elif thing.t == str:
                attrs['_saved_field_data'][name] = ""
            elif thing.t == bytes:
                attrs['_saved_field_data'][name] = b""
            elif thing.t == bool:
                attrs['_saved_field_data'][name] = False
            else:
                attrs['_saved_field_data'][name] = None

            # Create properties only for the specified fields.
            # We don't want to override global get/set behavior.
            def make_getter(n):
                def getter(self):
                    # Try to get from dirty, otherwise get from saved.
                    return self._dirty_field_data.get(
                        n, self._saved_field_data[n])
                getter.__name__ = n
                return getter

            def make_setter(n):
                def setter(self, value):
                    # TODO: run validators here (enforce types, etc.)
                    self._saved_field_data[n] = value
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
        # Copy so they're not shared between all instances
        self._dirty_field_data = self._dirty_field_data.copy()
        self._saved_field_data = self._saved_field_data.copy()

        # Populate initial state from the kwargs
        # TODO: This might be dirty data?
        self._saved_field_data.update(zone=zone, **kwargs)

        # We must have an id. If it wasn't specified, UUID it.
        self.id = kwargs.get('id', str(uuid4()))

        # Must also have a zone. But we can't generate this one.
        assert self.zone, "DO must have a zone."

    def serialize(self):
        # TODO: This will eventually be a "save" method, which only serializes
        # the dirty state.
        return json.dumps(self._saved_field_data)


class DistributedObjectClassRegistry:
    def __init__(self, *args):
        # TODO: Validate these are actually DO subclasses
        self._classes = args

    def __getitem__(self, classname: str):
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
        # TODO: The actual packet parsing should happen here too
        self._instances.append(obj)
        self.create_callback(obj)

    def update(self, obj_id: str, fields: dict):
        # TODO: Update plumbing is missing
        obj = None
        self.update_callback(obj)

    def delete(self, obj_id: str):
        obj = self[obj_id]
        self._instances.remove(obj)
        self.delete_callback(obj)

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