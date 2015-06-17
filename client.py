import asyncio
import json
from settings import MAX_PACKET_SIZE


class PubSubClient():
    _loop = None
    _reader = None
    _writer = None
    finished = False

    def setup(self):
        raise NotImplementedError()

    def object_created(self, distributed_object):
        # Unlike the other hooks, this one isn't required.
        pass

    def handle_message(self, channel: str, data: str):
        raise NotImplementedError()

    # Core Functions
    def subscribe(self, channel):
        self._send("sub:{}".format(channel))

    def unsubscribe(self, channel):
        self._send("unsub:{}".format(channel))

    def run(self):
        self._loop = asyncio.get_event_loop()
        self._loop.run_until_complete(self.establish_connection())
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            pass
        self._loop.close()

    # TODO: Audit all functions for private vs public
    @asyncio.coroutine
    def establish_connection(self):
        # Establish the socket
        self._reader, self._writer = yield from asyncio.open_connection(
            '127.0.0.1', 8888, loop=self._loop)

        # TODO: Authentication

        # Schedule any worker tasks
        asyncio.async(self.receive(), loop=self._loop)
        self.setup()

    @asyncio.coroutine
    def receive(self):
        msg = None
        while not self.finished:
            try:
                msg = yield from self._reader.read(MAX_PACKET_SIZE)
                if not msg:
                    # The server disconnected
                    yield from self.close()
            except (asyncio.CancelledError, asyncio.TimeoutError):
                print("Cancelled or Timeout")
                raise
            except Exception as exc:
                print("Something happened!", exc)
                yield from self.close()
            message = json.loads(msg.decode('utf8'))
            self.handle_message(message['channel'], message['data'])

    def _send(self, data):
        print('Sending:', data)
        self._writer.write(data.encode() + b"\n")

    @asyncio.coroutine
    def close(self):
        print("Closing")
        self.finished = True
        self._loop.stop()
