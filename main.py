"""
Pastry is a DistributedObject architecture that makes creating MMO games easy
as pie!
"""
import asyncio
import sys
from uuid import uuid4
from agent import PastryAgent
from client import PastryClient
from distributed_objects import DistributedObject, Field, \
    DistributedObjectClassRegistry
from zone import PastryZone


class Message(DistributedObject):
    text = Field(str)

    def __str__(self):
        return self.text


# Register all DOs here; this variable propagates to all the various components
CHAT_REGISTRY = DistributedObjectClassRegistry(
    Message
)


# TODO: Clients should be able to run before/after a connection
class ChatClient(PastryClient):
    registry = CHAT_REGISTRY
    account_id = str(uuid4())

    def setup(self):
        # Join a zone or two
        self.subscribe("chat")
        asyncio.async(self.heartbeat(), loop=self._loop)

    @asyncio.coroutine
    def heartbeat(self):
        while not self.finished:
            m = Message(owner=self.account_id, text="Heartbeat", zone="chat")
            self.save(m)
            yield from asyncio.sleep(5.0)

    def object_created(self, distributed_object):
        print(distributed_object.owner, distributed_object.text)


class ChatAgent(PastryAgent):
    registry = CHAT_REGISTRY

    log_color = "\033[93m"
    log_name = "Agent"

    def authenticate(self, *args, **kwargs):
        # TODO: I think this should return the user's token? Ideally, that's
        # never disclosed.
        return True


class ChatZone(PastryZone):
    zone_id = "chat"
    registry = CHAT_REGISTRY

    log_color = "\033[92m"
    log_name = "Zone"

    # TODO: Trigger -- On message create, rotate out (delete) any old messages
    # TODO: Trigger -- On join and leave, display messages
    def object_created(self, obj: DistributedObject):
        self.log("messages:", len(self.objects))

    def object_updated(self, obj: DistributedObject):
        self.log(obj, "was updated.")

    def object_deleted(self, obj: DistributedObject):
        self.log(obj, "was deleted.")


class MultiServer:
    """Run several backend server instances in one go. You really shouldn't
    use this in production, but it's quite useful in development.

    Example usage:
    m = MultiServer(MyZone1, MyZone2, MyZone3, MyAgent)
    m.run()
    """
    def __init__(self, *server_classes):
        self._loop = asyncio.get_event_loop()
        self.servers = [c(loop=self._loop) for c in server_classes]

    def run(self):
        """Start each server process then run a complete event loop."""
        for c in self.servers:
            c.startup()

        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            print("\nKeyboard Interrupt: shutting down...")

        for c in self.servers:
            c.shutdown()


if __name__ == "__main__":
    thing = sys.argv[1]
    if thing == 'server':
        to_start = MultiServer(ChatZone, ChatAgent)
    elif thing == 'client':
        to_start = ChatClient()
    else:
        raise ValueError('Must be `server` or `client`')
    to_start.run()
