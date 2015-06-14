"""
Pastry is a DistributedObject architecture that makes creating MMO games easy as pie!
"""
import asyncio
import sys
from agent import PubSubAgent
from client import PubSubClient
from zone import ZoneServer


class HeartbeatClient(PubSubClient):
    def setup(self):
        self.subscribe("zone-1")
        self.subscribe("zone-2")
        asyncio.async(self.heartbeat(), loop=self._loop)

    @asyncio.coroutine
    def heartbeat(self):
        while not self.finished:
            self._send("Heartbeat")
            yield from asyncio.sleep(1.0)

    def handle_message(self, data):
        print('Receiving:', data)


class TestAgent(PubSubAgent):
    def authenticate(self, *args, **kwargs):
        return True

    def handle_redis_message(self, message):
        print("Received (redis):", message)
        print("Echoing down to everyone...")
        self.broadcast("global", message)

    @asyncio.coroutine
    def handle_message(self, sender, data):
        message = data.decode('utf8')
        # Subscription requests are already handled; must be a
        # DistributedObject create/update.
        # TODO: Check that said DO is allowed to be created/updated
        print("Handle {} from {}".format(data, sender))
        yield from self.broadcast("channel will go here", data)


class HeartbeatZone(ZoneServer):
    zone_id = "zone-1"

    def handle_redis_message(self, message):
        print("I got a message:", message)


if __name__ == "__main__":
    thing = sys.argv[1]  # python main.py FOO
    if thing == 'agent':
        to_start = TestAgent()
    elif thing == 'client':
        to_start = HeartbeatClient()
    else:
        raise ValueError('Must be server, client or ai')
    to_start.run()