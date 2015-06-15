from base import RedisServer


class ZoneServer(RedisServer):
    """Persists state, makes changes to the state, and broadcasts the state so
    it gets to the right people.
    """
    zone_id = None

    def __init__(self):
        if not self.zone_id:
            raise NotImplementedError("Must have a zone_id on the zone server")

        super().__init__()
        self.register_channel(self.zone_id)
        self.objects = []