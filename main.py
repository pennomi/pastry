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
    owner = Field(str)
    text = Field(str)

    def serialize(self):
        return json.dumps({
            "id": self.id,
            "owner": self.owner,
            "text": self.text
        })


class HeartbeatClient(PubSubClient):
    account_id = str(uuid4())
    messages = []

    # TODO: Clients should be able to run before/after a connection

    def setup(self):
        # Join a zone
        self.subscribe("zone-1")
        self.subscribe("zone-2")
        asyncio.async(self.heartbeat(), loop=self._loop)

    @asyncio.coroutine
    def heartbeat(self):
        while not self.finished:
            m = Message(owner=self.account_id, text="Heartbeat")
            self._send(m.serialize())
            yield from asyncio.sleep(5.0)

    def handle_message(self, channel, data):
        # TODO: This should have channel data in it
        print('Receiving:', channel, data)
        if 'hello' not in channel:
            self.messages.append(data)
            print('messages:', len(self.messages))


class TestAgent(PubSubAgent):
    def authenticate(self, *args, **kwargs):
        # TODO: I think this should return the user's PK?
        return True

    @asyncio.coroutine
    def handle_client_message(self, sender, data):
        message = data.decode('utf8')
        # Subscription requests are already handled; must be a
        # DistributedObject create/update.
        # TODO: Check that the message is permitted; if not, kill.
        print("Received `{}` from `{}`".format(data, sender))
        # Once we know the message is allowed, send it to the zone server
        # TODO: How to know what zone this should be in anyway
        # TODO: Maybe it's a required attr on the DO
        self.redis_broadcast("zone-1.Message.create", message)


class HeartbeatZone(ZoneServer):
    zone_id = "zone-1"

    def handle_redis_message(self, channel, message):
        print("Received:", channel, message)
        if channel.startswith("zone-1.Message"):
            data = json.loads(message)
            self.objects.append(Message(**data))
            print("A total of {} messages".format(len(self.objects)))
        # TODO: If it's a hello message, broadcast out the full state to the
        if "hello" in channel:
            data = json.loads(message)
            for o in self.objects:
                self.redis_broadcast(
                    "{}.{}".format(data['id'], "zone-1.Message"),
                    o.serialize())

        # new person, on their private channel


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