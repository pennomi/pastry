import asyncio


class MultiServer:
    """Run several backend server instances in one go. You really shouldn't
    use this in production, but it's quite useful in development.

    Example usage:
    m = MultiServer(MyZone1, MyZone2, MyZone3, MyAgent)
    m.run()
    """
    def __init__(self, *server_classes):
        self._loop = asyncio.get_event_loop()
        self.servers = [c(loop=self._loop) for c in server_classes]

    def run(self):
        """Start each server process then run a complete event loop."""
        for c in self.servers:
            c.startup()

        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            print("\nKeyboard Interrupt: shutting down...")

        for c in self.servers:
            c.shutdown()
