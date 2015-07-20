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

    def __init__(self, loop=None):
        if not loop:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self.objects = DistributedObjectState(
            self.object_created, self.object_updated, self.object_deleted)

    def setup(self):
        raise NotImplementedError()

    # These are to be overridden by the implementer of the Client
    def object_created(self, distributed_object: DistributedObject):
        pass

    def object_updated(self, distributed_object: DistributedObject):
        pass

    def object_deleted(self, distributed_object: DistributedObject):
        pass

    def save(self, *objects: DistributedObject):
        """Takes a list of distributed objects and sends them across the
        network to be saved.
        """
        for o in objects:
            method = "update" if o.created else "create"

            # Build the channel
            c = Channel(target=o.zone, method=method,
                        code_name=None if o.created else o.__class__.__name__)
            # Send via the network
            self._send(c, o.serialize())
            # Move the dirty data over to the clean data
            o._save()

    def _handle_message(self, channel: Channel, data: str):
        # TODO: Also handle deleting DOs
        # TODO: A lot of this is repeated code on the client/zone. Can it be
        # generalized?
        if channel.method == 'create':
            class_ = self.registry[channel.code_name]
            created_object = class_(**json.loads(data))
            # TODO: Maybe this should take in the registry or something
            self.objects.create(created_object)
        elif channel.method == 'update':
            kwargs = json.loads(data)
            self.objects.update(**kwargs)

    # Core Functions
    def subscribe(self, channel_name: str):
        c = Channel(target=channel_name, method="join")
        self._send(c, "")

    def unsubscribe(self, channel_name: str):
        c = Channel(target=channel_name, method="leave")
        self._send(c, "")

    def run(self):
        self._loop.run_until_complete(self.establish_connection())
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            pass
        self._loop.close()

    # TODO: Audit all functions for private vs public
    # TODO: Make sure that the client can run the GUI even when not connected
    # to the server
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
                    self._handle_message(c, message['data'])
                except ValueError as e:
                    # Didn't get the full message, save for next time.
                    leftovers = m

    def _send(self, channel: Channel, data: str):
        channel_data = str(channel).encode()
        self._writer.write(channel_data + b"|" + data.encode() + b"\n")

    @asyncio.coroutine
    def close(self):
        print("Closing")
        self.finished = True
        self._loop.stop()
