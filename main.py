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
from util import Channel
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
            # TODO: I want this to be more "magical". Like `m.save()`
            # TODO: `m.distribute()`?
            c = Channel(target=m.zone, method="create",
                        code_name=m.__class__.__name__)
            self._send(c, m.serialize())
            yield from asyncio.sleep(5.0)

    def object_created(self, distributed_object):
        print('messages:', len(self.objects))

    def object_updated(self, distributed_object):
        print('messages:', len(self.objects))

    def object_deleted(self, distributed_object):
        print('messages:', len(self.objects))


class ChatAgent(PastryAgent):
    log_color = "\033[93m"
    log_name = "Agent"

    registry = CHAT_REGISTRY

    def authenticate(self, *args, **kwargs):
        # TODO: I think this should return the user's PK?
        return True


class ChatZone(PastryZone):
    log_color = "\033[92m"
    log_name = "Zone"

    registry = CHAT_REGISTRY
    zone_id = "chat"

    # TODO: Show a pattern here for logic. Both time-based and trigger-based.
    # TODO: Time -- Once every N seconds, do a thing.
    # TODO: Trigger -- On message create, rotate out (delete) any old messages
    # TODO: Trigger -- On entry and exit, display messages
    def object_created(self, obj: DistributedObject):
        self.log("messages:", len(self.objects))

    def object_updated(self, obj: DistributedObject):
        self.log(obj, "was updated.")

    def object_deleted(self, obj: DistributedObject):
        self.log(obj, "was deleted.")


# TODO: A MultiServer that can run any number of registered Zone and Agent
# servers simultaneously. This should also configure log output to identify
# the source.
# You wouldn't deploy the MultiServer in production, but it'd be insanely
# useful in development.
class MultiServer:
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
            pass

        for c in self.servers:
            c.shutdown()


if __name__ == "__main__":
    thing = sys.argv[1]  # python main.py FOO
    if thing == 'server':
        to_start = MultiServer(ChatZone, ChatAgent)
    elif thing == 'client':
        to_start = ChatClient()
    else:
        raise ValueError('Must be server or client')
    to_start.run()
