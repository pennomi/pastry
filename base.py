import asyncio
from uuid import uuid4
import redis
import signal


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
        self.zones = []

    def run(self):
        print("Starting StateServer")


class Client:
    is_ai = False
    channels = []
    objects = {}

    def __init__(self):
        self._r = redis.StrictRedis(host='localhost', port=6379, db=0)
        self._p = self._r.pubsub()
        self.loop = asyncio.get_event_loop()
        self.loop.add_signal_handler(signal.SIGINT, self.loop.stop)
        self.loop.add_signal_handler(signal.SIGTERM, self.loop.stop)

    def register_channel(self, channel_name):
        self.channels.append(channel_name)
        self._p.psubscribe("{}.*".format(channel_name))
        self._r.publish("{}.hello".format(channel_name), '{"hello": "world"}')

    def unregister_channel(self, channel_name):
        self.channels.remove(channel_name)
        self._p.punsubscribe("{}.*".format(channel_name))

    def create_object(self, distributed_object):
        self.objects[distributed_object.id] = distributed_object

    def delete_object(self, obj):
        del self.objects[obj.id]

    def _listen(self):
        message = self._p.get_message()
        if message:
            print("-->", message)
        self.loop.call_later(0.001, self._listen)

    def run(self):
        print("Starting Client...")
        # TODO: Refactor this into a base redis client class
        self.loop.call_soon(self._listen)
        self.loop.run_forever()


class AI(Client):
    is_ai = True  # TODO: Think up something more secure than this

    def run(self):
        print("Starting AI")