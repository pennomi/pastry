# coding=utf-8
"""The internal messaging server is the base class for all pubsub-based servers.
Specifically, this means the Agent and Zone servers.
"""

import asyncio
import redis
from util import Channel


class InternalMessagingServer:
    """InternalMessagingServers connect to Redis pubsub and maintain a list of
    interested channels.
    """
    log_color = "\033[94m"
    log_name = "Unknown"
    server = None

    def __init__(self, loop=None):
        if not loop:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self.channels = []
        self._init_redis()

    def log(self, *messages):
        message = " ".join(str(m) for m in messages)
        print("{c}\033[1m{n: <16}\033[0m{m}".format(
            c=self.log_color, n=self.log_name, m=message))

    def _init_redis(self):
        self.log("Connecting to Redis...")
        self._redis = redis.StrictRedis(host='localhost', port=6379, db=0)
        self._pubsub = self._redis.pubsub()
        # Must register a channel before starting the loop. This can probably
        # be the global channel, since everyone needs that.
        # TODO: Maybe have 2 channels: `public` and `internal`
        self.internal_subscribe("global")

    def _handle_internal_message(self, channel: Channel, message: str):
        raise NotImplementedError()

    def internal_broadcast(self, channel: Channel, message: str):
        """Send a message to on a channel to all internal listeners."""
        self._redis.publish(str(channel), message)

    def internal_subscribe(self, channel_name: str):
        """Start listening to a Redis pubsub channel."""
        self.log("Subscribing", channel_name)
        self.channels.append(channel_name)
        self._pubsub.psubscribe("{}.*".format(channel_name))

    def internal_unsubscribe(self, channel_name: str):
        """Stop listening to a Redis pubsub channel."""
        self.log("Unsubscribing", channel_name)
        self.channels.remove(channel_name)
        self._pubsub.punsubscribe("{}.*".format(channel_name))

    async def _redis_listen(self):
        while True:
            # TODO: Do all redis pieces need to run in an executor?
            message = self._pubsub.get_message()
            if message and message['type'] not in ['psubscribe', 'punsubscribe']:
                channel = Channel.parse(message['channel'].decode('utf8'))
                self._handle_internal_message(
                    channel, message['data'].decode('utf8'))
            await asyncio.sleep(0.001)

    def startup(self):
        asyncio.ensure_future(self._redis_listen())

    def shutdown(self):
        pass

    def run(self):
        self.startup()
        try:
            # TODO: Should this loop not be defined on self?
            self._loop.run_forever()
        except KeyboardInterrupt:
            pass
