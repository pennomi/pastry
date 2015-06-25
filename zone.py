import json
from base import InternalMessagingServer
from distributed_objects import DistributedObjectState, DistributedObject
from util import Channel


class PastryZone(InternalMessagingServer):
    """Persists state, makes changes to the state, and broadcasts the state so
    it gets to the right people.
    """
    registry = None
    zone_id = None

    def __init__(self):
        super().__init__()

        # Check that registry is set up
        if not self.registry:
            raise NotImplementedError("`registry` must be on zone subclasses")

        # Always listen for itself.
        if not self.zone_id:
            raise NotImplementedError("Must have a zone_id on the zone server")
        # noinspection PyTypeChecker
        self.internal_subscribe(self.zone_id)

        # Set up the object state tracking
        self.objects = DistributedObjectState(
            self.object_created, self.object_updated, self.object_deleted)

        # Run any game-specific logic
        self.setup()

    def setup(self):
        pass

    def object_created(self, obj: DistributedObject):
        pass

    def object_updated(self, obj: DistributedObject):
        pass

    def object_deleted(self, obj: DistributedObject):
        pass

    def handle_internal_message(self, channel, message):
        print("Received:", channel, message)

        if channel.method == "create":
            data = json.loads(message)
            # An object was created! Add it like normal.
            class_ = self.registry[channel.code_name]
            self.objects.create(class_(**data))

        elif channel.method == "update":
            data = json.loads(message)
            obj = self.objects.update(data['id'], data)
        # TODO: Delete, Call, Leave

        elif channel.method == "join":
            # Someone just joined! Let's sync down our zone's state.
            print("{} joined. Syncing server state ({} objects)".format(
                message, len(self.objects)))
            for o in self.objects:
                output_channel = Channel(
                    # The message here is the user's ID.
                    target=message, method="create",
                    code_name=o.__class__.__name__)
                self.internal_broadcast(output_channel, o.serialize())
