# coding=utf-8
"""The Zone server handles the logic for a specific vertical of gameplay."""
import json
from typing import List

from base import InternalMessagingServer
from distributed_objects import DistributedObjectState, DistributedObject
from util import Channel


class PastryZone(InternalMessagingServer):
    """Persists state, makes changes to the state, and broadcasts the state so
    it gets to the right people.
    """
    registry = None
    zone_id = ""

    def __init__(self, loop=None):
        super().__init__(loop=loop)

        # Check that registry is set up
        if not self.registry:
            raise AttributeError("`registry` must be on zone subclasses")

        # Always listen for itself.
        if not self.zone_id:
            raise AttributeError("Must have a zone_id on the zone server")
        self.internal_subscribe(self.zone_id)

        # Set up the object state tracking
        self.objects = DistributedObjectState(
            self.object_created, self.object_updated, self.object_deleted)

        # Run any game-specific logic
        self.setup()

    def save(self, *objects: List[DistributedObject]):
        """Save one or more distributed objects, sending those changes through
        the network.
        """
        # TODO: This pattern is cumbersome. How else could it be implemented?
        for o in objects:
            if o._deleted:
                method = "delete"
            elif o.created:
                method = "update"
            else:
                method = "create"

            # Build the channel
            c = Channel(target=o.zone, method=method,
                        code_name=None if o.created else o.__class__.__name__)

            # Add it locally immediately
            if method == "create":
                self.objects.create(o)

            # Or remove it immediately
            if method == "delete":
                self.objects.delete(o.id)

            # Send via the network
            self.internal_broadcast(c, o.serialize(
                for_create=method == "create"))
            # Move the dirty data over to the clean data
            o._save()

    def setup(self):
        pass

    def object_created(self, obj: DistributedObject):
        """Callback for object creation, to be implemented by a subclass."""
        pass

    def object_updated(self, obj: DistributedObject):
        """Callback for object updates, to be implemented by a subclass."""
        pass

    def object_deleted(self, obj: DistributedObject):
        """Callback for object deletion, to be implemented by a subclass."""
        pass

    def client_connected(self, client_id: str):
        """Callback for client connection, to be implemented by a subclass."""
        pass

    def client_disconnected(self, client_id: str):
        """Callback for client disconnect, to be implemented by a subclass."""
        pass

    def _handle_internal_message(self, channel, message):
        self.log("Received", channel)

        if channel.method == "create":
            kwargs = json.loads(message)
            class_ = self.registry[channel.code_name]
            self.objects.create(class_(**kwargs))

        elif channel.method == "update":
            kwargs = json.loads(message)
            self.objects.update(**kwargs)
        # TODO: Delete, Call

        elif channel.method == "join":
            # Someone just joined!
            self.client_connected(message)

            # Let's also sync down our zone's state.
            self.log("{} joined. Syncing server state ({} objects)".format(
                message, len(self.objects)))
            for o in self.objects:
                output_channel = Channel(
                    # The message here is the user's ID.
                    target=message, method="create",
                    code_name=o.__class__.__name__)
                self.internal_broadcast(
                    output_channel, o.serialize(for_create=True))

        elif channel.method == "leave":
            # Someone just left!
            self.client_disconnected(message)
