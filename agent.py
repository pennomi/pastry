import asyncio
import json
from uuid import uuid4
from base import InternalMessagingServer
from settings import MAX_PACKET_SIZE
from util import Channel


class ClientConnection:
    """Represents all the data pertaining to one client."""
    def __init__(self, r, w):
        # Upon connection, we assign this person a UUID.
        self.id = str(uuid4())
        self.reader, self.writer = r, w
        self.subscriptions = []

    def responds_to(self, channel: Channel) -> bool:
        # I always am interested in myself
        if channel.target == self.id:
            return True
        # Otherwise I just check my zone subscriptions
        return channel.target in self.subscriptions

    def kill(self):
        pass  # TODO: Implement me! We need an easy way to kill off a client.

    def __repr__(self):
        return "<Client {}>".format(self.writer.get_extra_info('peername'))


class PastryAgent(InternalMessagingServer):
    """The agent is the secure gateway through which the client connects to
    the full system.

    On one side a secure TCP socket talks to the client, and on the other side
    a Redis pubsub connection speaks with the entire internal network.
    """
    loop = None
    connections = []
    finished = False

    def authenticate(self, *args, **kwargs) -> bool:
        raise NotImplementedError()

    def run(self):
        """Start the server process."""
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

        # TODO: Authenticate
        if not self.authenticate():
            self.finished = True

        # Sign up for internal private messages for this user
        self.internal_subscribe(connection.id)

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

        print("Close the socket for {}".format(connection))
        writer.close()
        self.connections.remove(connection)

    @asyncio.coroutine
    def read_message(self, sender: ClientConnection, data: bytes):
        for d in [_ for _ in data.split(b'\n') if _]:
            # Decode the message
            message = d.decode('utf8')

            # Subscription requests
            # TODO: Find a better
            if message.startswith('sub:'):
                zone_name = message[4:]
                print("Subscribing", sender, "to", zone_name)
                # TODO: Hang up on any requests that aren't permitted
                # TODO: (ie. can't subscribe to any subchannels: no `.`s)
                sender.subscriptions.append(zone_name)
                self.internal_subscribe(zone_name)
                # Trigger the sync the state of the subscription
                c = Channel(target=zone_name, method="join")
                self.internal_broadcast(c, sender.id)
            # Unsubscription request. No permission necessary.
            elif message.startswith('unsub:'):
                print("Unsubscribing", sender, "from", d)
                # TODO: Don't crash if it's not in the list
                sender.subscriptions.remove(message[6:])
                # TODO: Check all subscriptions to see if this is needed any
                # more. Others might still be using it!
                self.internal_unsubscribe(message[6:])
                c = Channel(target=message[6:], method="leave")
                self.internal_broadcast(c, sender.id)
            else:
                # This is a non-pubsub message; forward to the do handler
                yield from self.handle_client_message(sender, d)

    @asyncio.coroutine
    def handle_client_message(self, sender: ClientConnection, data: bytes):
        # TODO: This should receive channels too?
        message = data.decode('utf8')
        # Subscription requests are already handled; must be a
        # DistributedObject create/update.
        # TODO: Check that the message is permitted; if not, kill.
        print("Received `{}` from `{}`".format(data, sender))
        # Once we know the message is allowed, send it to the zone server
        # TODO: How to know what zone this should be in anyway
        # TODO: Maybe it's a required attr on the DO
        # TODO: No hardcoding the channels!
        channel = Channel(
            target="chat", method="create", code_name="Message")
        self.internal_broadcast(channel, message)

    def handle_internal_message(self, channel, message):
        """Whenever the agent receives an internal message, it's forwarded
        to all relevant clients.
        """
        asyncio.async(self.client_broadcast(channel, message))

    @asyncio.coroutine
    def client_broadcast(self, channel: Channel, data: str):
        connections = [c for c in self.connections if c.responds_to(channel)]
        # TODO: Handle channels better on the client itself
        print("Sending: {} to {} connections".format(
            data, len(connections)))
        to_send = json.dumps({
            "channel": str(channel),
            "data": data
        })
        for c in connections:
            try:
                c.writer.write(to_send.encode() + b'\n')
                yield from c.writer.drain()
            except ConnectionResetError:
                print("Lost connection to {}. Killing...".format(c))
                self.connections.remove(c)
