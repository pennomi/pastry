import asyncio
import redis


class RedisServer:
    def __init__(self):
        self.channels = []
        print("Connecting to Redis...")
        self._redis = redis.StrictRedis(host='localhost', port=6379, db=0)
        self._pubsub = self._redis.pubsub()
        # Must register a channel before starting the loop. This can probably
        # be the global channel, since everyone needs that.
        self.register_channel("global")
        # TODO: Maybe have 2 channels: `public` and `internal`
        self.loop = asyncio.get_event_loop()

    def handle_redis_message(self, channel: str, message: str):
        raise NotImplementedError()

    def redis_broadcast(self, channel: str, message: str):
        self._redis.publish(channel, message)

    def register_channel(self, channel_name):
        print("Registering", channel_name)
        self.channels.append(channel_name)
        self._pubsub.psubscribe("{}.*".format(channel_name))

    def unregister_channel(self, channel_name):
        print("Unregistering", channel_name)
        self.channels.remove(channel_name)
        self._pubsub.punsubscribe("{}.*".format(channel_name))

    def _redis_listen(self):
        # TODO: Check if there's a better pattern for this
        message = self._pubsub.get_message()
        if message and not message['type'] == 'psubscribe':
            self.handle_redis_message(message['channel'].decode('utf8'),
                                      message['data'].decode('utf8'))
        self.loop.call_later(0.001, self._redis_listen)

    def run(self):
        print("Starting RedisServer")
        self.loop.call_soon(self._redis_listen)
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass