import asyncio
from base import RedisServer
from settings import MAX_PACKET_SIZE


class ClientConnection:
    def __init__(self, r, w):
        self.reader, self.writer = r, w
        self.subscriptions = []

    def kill(self):
        pass  # TODO: Implement me! We need an easy way to kill off a client.

    def __repr__(self):
        return "<Client {}>".format(self.writer.get_extra_info('peername'))


class PubSubAgent(RedisServer):
    """The agent is the secure gateway through which the client connects to
    the full system.

    On one side a secure TCP socket talks to the client, and on the other side
    a Redis pubsub connection speaks with the entire internal network.
    """
    loop = None
    connections = []
    finished = False

    # TODO: necessary functions
    # receive message from redis (then forward it to the right people)
    # handle a subscription
    # handle an unsubscription

    def authenticate(self, *args, **kwargs) -> bool:
        raise NotImplementedError()

    def handle_message(self, sender: ClientConnection, data: bytes):
        raise NotImplementedError()

    def handle_redis_message(self, message):
        raise NotImplementedError()

    def run(self):
        coroutine = asyncio.start_server(
            self.create_client_connection, '127.0.0.1', 8888, loop=self.loop)
        server = self.loop.run_until_complete(coroutine)

        # Serve requests until CTRL+c is pressed
        print('Serving on {}'.format(server.sockets[0].getsockname()))
        super().run()

        # Close the server
        server.close()
        self.loop.run_until_complete(server.wait_closed())
        self.loop.close()

    @asyncio.coroutine
    def create_client_connection(self, reader, writer):
        """A unique instance of this coroutine is active for each connected
        client.
        """
        # Keep this connection around for a while
        connection = ClientConnection(reader, writer)
        self.connections.append(connection)
        address = writer.get_extra_info('peername')

        # TODO: Authenticate
        if not self.authenticate():
            self.finished = True

        while not self.finished:
            try:
                msg = yield from reader.read(MAX_PACKET_SIZE)
                if not msg:  # They've disconnected
                    break
            except (asyncio.CancelledError, asyncio.TimeoutError):
                print("Cancelled or Timeout")
                raise
            except Exception as exc:
                print("Something happened!", exc)
                break
            # Handle the message
            yield from self.read_message(connection, msg)

        print("Close the client socket for {}".format(address))
        writer.close()
        self.connections.remove(connection)

    @asyncio.coroutine
    def read_message(self, sender: ClientConnection, data: bytes):
        for d in [_ for _ in data.split(b'\n') if _]:
            # Decode the message
            message = d.decode('utf8')

            # Subscription requests
            if message.startswith('sub:'):
                print("Subscribing", sender, "to", d)
                # TODO: Hang up on any requests that aren't permitted
                sender.subscriptions.append(message[4:])
                # TODO: Sync the state of the subscription down
            # Unsubscription request. No permission necessary.
            elif message.startswith('unsub:'):
                print("Unsubscribing", sender, "from", d)
                # TODO: Don't crash if it's not in the list
                sender.subscriptions.remove(message[6:])
            else:
                # This is a non-pubsub message; forward to the subclass
                yield from self.handle_message(sender, d)

    @asyncio.coroutine
    def broadcast(self, channel: str, data: bytes):
        # TODO: Handle channels
        print("Sending: {} to {} connections".format(
            data, len(self.connections)))
        for c in self.connections.copy():
            try:
                c.writer.write(data)
                yield from c.writer.drain()
            except ConnectionResetError:
                print("Lost connection to {}. Killing...".format(c))
                self.connections.remove(c)
