import asyncio
import json
from distributed_objects import DistributedObjectState, DistributedObject
from settings import MAX_PACKET_SIZE
from util import Channel


class PastryClient:
    _loop = None
    _reader = None
    _writer = None
    finished = False
    registry = None

    def __init__(self):
        super().__init__()
        self.objects = DistributedObjectState(
            self.object_created, self.object_updated, self.object_deleted)

    def setup(self):
        raise NotImplementedError()

    def object_created(self, distributed_object: DistributedObject):
        pass

    def object_updated(self, distributed_object: DistributedObject):
        pass

    def object_deleted(self, distributed_object: DistributedObject):
        pass

    def handle_message(self, channel: Channel, data: str):
        # TODO: Also handle updating and deleting DOs
        print('Receiving:', channel, data)
        # TODO: A lot of this is repeated code on the client/zone. Can it be
        # generalized?
        if channel.method == 'create':
            class_ = self.registry[channel.code_name]
            kwargs = json.loads(data)
            created_object = class_(**kwargs)
            # TODO: Maybe this should take in the registry or something
            self.objects.create(created_object)
        elif channel.method == 'update':
            kwargs = json.loads(data)
            # TODO: Maybe the kwargs['id'] isn't necessary? We could force `id`
            # and `zone` to always be serialized.
            self.objects.update(kwargs['id'], kwargs)

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
        leftovers = b''
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
            msg = leftovers + msg
            leftovers = b''
            messages = msg.split(b"\n")
            for m in messages:
                m = m.strip()
                if not m:
                    continue
                try:
                    message = json.loads(m.decode('utf8'))
                    c = Channel.parse(message['channel'])
                    self.handle_message(c, message['data'])
                except ValueError as e:
                    # Didn't get the full message, save for next time.
                    leftovers = m

    def _send(self, data):
        print('Sending:', data)
        self._writer.write(data.encode() + b"\n")

    @asyncio.coroutine
    def close(self):
        print("Closing")
        self.finished = True
        self._loop.stop()
