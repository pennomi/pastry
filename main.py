"""
Pastry is a DistributedObject architecture that makes creating MMO games easy as pie!
"""
import asyncio
import json
import sys
from uuid import uuid4
from agent import PubSubAgent
from client import PubSubClient
from distributed_objects import DistributedObject, Field
from zone import ZoneServer


class Message(DistributedObject):
    text = Field(str)


# Register all DOs here; this variable propagates to all the various components
TEST_REGISTRY = [Message]


class HeartbeatClient(PubSubClient):
    registry = TEST_REGISTRY

    account_id = str(uuid4())
    messages = []

    # TODO: Clients should be able to run before/after a connection

    def setup(self):
        # Join a zone or two
        self.subscribe("chat")
        self.subscribe("zone-1")
        asyncio.async(self.heartbeat(), loop=self._loop)

    @asyncio.coroutine
    def heartbeat(self):
        while not self.finished:
            m = Message(owner=self.account_id, text="Heartbeat", zone="zone-1")
            self._send(m.serialize())
            yield from asyncio.sleep(5.0)

    def object_created(self, distributed_object):
        pass

    # TODO: Push this into the Client code. Auto-create the DOs then trigger.
    def handle_message(self, channel, data):
        # TODO: This should have channel data in it
        print('Receiving:', channel, data)
        # TODO: Handle "leave" messages too
        if 'join' not in channel:
            # TODO: m = Message(**stuff)
            self.messages.append(data)
            print('messages:', len(self.messages))


class TestAgent(PubSubAgent):
    registry = TEST_REGISTRY

    def authenticate(self, *args, **kwargs):
        # TODO: I think this should return the user's PK?
        return True


class HeartbeatZone(ZoneServer):
    registry = TEST_REGISTRY
    zone_id = "zone-1"

    # TODO: Show a pattern here for logic. Both time-based and trigger-based.
    # TODO: Time -- Once every N seconds, do a thing.
    # TODO: Trigger -- On message create, rotate out (delete) any old messages
    # TODO: Trigger -- On entry and exit, display messages

    def handle_redis_message(self, channel, message):
        # TODO: This whole method should be reduced in scope
        print("Received:", channel, message)
        # Handle creating of DOs
        if channel.startswith("{}.Message".format(self.zone_id)):
            data = json.loads(message)
            self.objects.append(Message(**data))
            print("A total of {} messages".format(len(self.objects)))
        # If it's a join message, broadcast out the full state to the
        # entrant on their private channel
        # TODO: Handle "leave" messages too
        if "join" in channel:
            data = json.loads(message)
            for o in self.objects:
                self.redis_broadcast(
                    "{}.{}".format(data['id'], "zone-1.Message"),
                    o.serialize())


# TODO: A MultiServer that can run any number of registered Zone and Agent
# servers simultaneously. This should also configure log output to identify
# the source.
# You wouldn't deploy the MultiServer in production, but it'd be insanely
# useful in development.


if __name__ == "__main__":
    thing = sys.argv[1]  # python main.py FOO
    if thing == 'agent':
        to_start = TestAgent()
    elif thing == 'client':
        to_start = HeartbeatClient()
    elif thing == 'zone':
        to_start = HeartbeatZone()
    else:
        raise ValueError('Must be server, client or ai')
    to_start.run()