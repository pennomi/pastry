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

    def setup(self):
        self.subscribe("zone-1")
        # self.subscribe("zone-2")
        asyncio.async(self.heartbeat(), loop=self._loop)

    @asyncio.coroutine
    def heartbeat(self):
        while not self.finished:
            m = Message(owner=self.account_id, text="Heartbeat")
            self._send(m.serialize())
            yield from asyncio.sleep(5.0)

    def handle_message(self, data):
        print('Receiving:', data)


class TestAgent(PubSubAgent):
    def authenticate(self, *args, **kwargs):
        return True

    def handle_redis_message(self, channel, message):
        print("Received (redis):", message)
        print("Echoing down to everyone...", channel, message)
        asyncio.async(self.broadcast_to_clients(channel, message.encode()))

    @asyncio.coroutine
    def handle_client_message(self, sender, data):
        message = data.decode('utf8')
        # Subscription requests are already handled; must be a
        # DistributedObject create/update.
        # TODO: Check that the message is permitted; if not, kill.
        print("Handle {} from {}".format(data, sender))
        #yield from self.broadcast_to_clients("channel will go here", data)
        # Once we know the message is allowed, send it to the zone server
        # TODO: How to know what zone this should be in anyway
        # TODO: Maybe it's a required attr on the DO
        self.redis_broadcast("zone-1.Message.create", message)


class HeartbeatZone(ZoneServer):
    zone_id = "zone-1"

    def handle_redis_message(self, channel, message):
        print("Redis message:", channel, message)
        if channel.startswith("zone-1.Message"):
            data = json.loads(message)
            self.objects.append(Message(**data))
            print("A total of {} messages".format(len(self.objects)))


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