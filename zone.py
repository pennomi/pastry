from base import RedisServer


class ZoneServer(RedisServer):
    """Persists state, makes changes to the state, and broadcasts the state so
    it gets to the right people.
    """
    def __init__(self):
        super().__init__()
        self.register_channel("zone-1")

    def handle_redis_message(self, message):
        print(message)

    def _redis_listen(self):
        # TODO: Check if there's a better pattern for this
        message = self._pubsub.get_message()
        if message:
            self.handle_redis_message(message)
        self.loop.call_later(0.001, self._redis_listen)
