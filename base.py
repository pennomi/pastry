from uuid import uuid4


class DistributedObject:
    # noinspection PyShadowingBuiltins
    def __init__(self, *, id=None, owner=None, **kwargs):
        if not id:
            uuid = uuid4()
        self.id = id
        self.owner = owner

        for key, value in kwargs.items():
            # TODO: Check these are the metaclass fields
            setattr(self, key, value)

    def save(self):
        print("TODO: Send state to server")


class StateServer:
    def __init__(self):
        self.zones = {}

    def run(self):
        print("Starting StateServer")


class Client:
    is_ai = False
    interests = []
    objects = {}

    def create_object(self, distributed_object):
        self.objects[distributed_object.id] = distributed_object

    def delete_object(self, obj):
        del self.objects[obj.id]

    def run(self):
        print("Starting Client")


class AI(Client):
    is_ai = True  # TODO: Think up something more secure than this

    def run(self):
        print("Starting AI")