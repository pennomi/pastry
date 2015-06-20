import asyncio
import redis
from util import Channel


class InternalMessagingServer:
    def __init__(self):
        self.channels = []
        print("Connecting to Redis...")
        self._redis = redis.StrictRedis(host='localhost', port=6379, db=0)
        self._pubsub = self._redis.pubsub()
        # Must register a channel before starting the loop. This can probably
        # be the global channel, since everyone needs that.
        self.internal_subscribe("global")
        # TODO: Maybe have 2 channels: `public` and `internal`
        self.loop = asyncio.get_event_loop()

    def handle_internal_message(self, channel: Channel, message: str):
        raise NotImplementedError()

    def internal_broadcast(self, channel: Channel, message: str):
        self._redis.publish(str(channel), message)

    def internal_subscribe(self, channel_name: str):
        print("Registering", channel_name)
        self.channels.append(channel_name)
        self._pubsub.psubscribe("{}.*".format(channel_name))

    def internal_unsubscribe(self, channel_name: str):
        print("Unregistering", channel_name)
        self.channels.remove(channel_name)
        self._pubsub.punsubscribe("{}.*".format(channel_name))

    def _redis_listen(self):
        # TODO: Check if there's a better pattern for this
        message = self._pubsub.get_message()
        if message and not message['type'] == 'psubscribe':
            channel = Channel.parse(message['channel'].decode('utf8'))
            self.handle_internal_message(
                channel, message['data'].decode('utf8'))
        self.loop.call_later(0.001, self._redis_listen)

    def run(self):
        print("Starting RedisServer")
        self.loop.call_soon(self._redis_listen)
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass