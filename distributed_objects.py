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
                fdel=None, doc=name  # TODO: Use the "help" param on the field
            )

        return super().__new__(mcs, classname, baseclasses, attrs)


class DistributedObject(metaclass=DistributedObjectMetaclass):
    """A very simple implementation of the DistributedObjectMetaclass."""
    # Required attributes
    id = Field(str)
    owner = Field(str)  # Null means owned by the ZoneServer
    # zone = Field(str)  # TODO: Maybe a nullable zone; it's global otherwise

    def __init__(self, **kwargs):
        super().__init__()
        # We must have an id. If it wasn't specified, UUID it.
        self.id = kwargs.get('id', str(uuid4()))

        # Copy so they're not shared between all instances
        self._dirty_field_data = self._dirty_field_data.copy()
        self._saved_field_data = self._saved_field_data.copy()

        # Populate from the kwargs
        self._saved_field_data.update(kwargs)