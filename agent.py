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
    _loop = None
    connections = []
    finished = False

    def authenticate(self, *args, **kwargs) -> bool:
        raise NotImplementedError()

    def startup(self):
        coroutine = asyncio.start_server(
            self._create_client_connection, '127.0.0.1', 8888, loop=self._loop)
        self.server = self._loop.run_until_complete(coroutine)
        super().startup()

    def run(self):
        """Start the server process."""
        self.startup()

        # Serve requests until CTRL+c is pressed
        self.log('Serving on {}'.format(self.server.sockets[0].getsockname()))
        super().run()

        # Close the server
        self.shutdown()

    def shutdown(self):
        self.server.close()
        self._loop.run_until_complete(self.server.wait_closed())
        self._loop.close()

    @asyncio.coroutine
    def _create_client_connection(self, reader, writer):
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
                self.log("Cancelled or Timeout")
                raise
            except Exception as exc:
                self.log("Something happened!", exc)
                break
            # Handle the message
            yield from self._read_message(connection, msg)

        self.log("Close the socket for {}".format(connection))
        writer.close()
        self.connections.remove(connection)

    @asyncio.coroutine
    def _read_message(self, sender: ClientConnection, data: bytes):
        for d in [_ for _ in data.split(b'\n') if _]:
            # Decode the message
            raw_message = d.decode('utf8')

            input_channel, message = raw_message.split("|")
            # TODO: Change this to join/leave and it becomes more elegant
            channel = Channel.parse(input_channel)

            # Subscription requests
            # TODO: Handle these channels properly
            if channel.method == 'subscribe':
                # TODO: Hang up on any requests that aren't permitted
                # TODO: (ie. can't subscribe to any subchannels: no `.`s)
                self.log("Subscribing", sender, "to", channel.target)
                sender.subscriptions.append(channel.target)
                self.internal_subscribe(channel.target)
                # Trigger the sync the state of the subscription
                c = Channel(target=channel.target, method="join")
                self.internal_broadcast(c, sender.id)
            # Unsubscription request. No permission necessary.
            elif channel.method == 'unsubscribe':
                self.log("Unsubscribing", sender, "from", d)
                # TODO: Don't crash if it's not in the list
                sender.subscriptions.remove(channel.target)
                # TODO: Check all subscriptions to see if this is needed any
                # more. Others might still be using it!
                self.internal_unsubscribe(channel.target)
                # TODO: Trigger a delete state for the leaver
                c = Channel(target=channel.target, method="leave")
                self.internal_broadcast(c, sender.id)
            else:
                # This is a non-pubsub message; forward to the do handler
                yield from self._handle_client_message(sender, channel, message)

    @asyncio.coroutine
    def _handle_client_message(self, sender: ClientConnection,
                               channel: Channel, message: str):
        # TODO: This should receive channels too?
        # Subscription requests are already handled; must be a
        # DistributedObject create/update/delete/call.
        # TODO: Check that the message is permitted; if not, kill.
        self.log("Received `{}` from `{}`".format(message, sender))
        # Once we know the message is allowed, send it to the zone server
        # TODO: Creating objects on the client here. Probably need the client
        # to send channel data too

        # Handle an update message
        kwargs = json.loads(message)
        self.internal_broadcast(channel, message)

    def _handle_internal_message(self, channel, message):
        """Whenever the agent receives an internal message, it's forwarded
        to all relevant clients.
        """
        asyncio.async(self.client_broadcast(channel, message), loop=self._loop)

    @asyncio.coroutine
    def client_broadcast(self, channel: Channel, data: str):
        connections = [c for c in self.connections if c.responds_to(channel)]
        # TODO: Handle channels better on the client itself
        self.log("Sending: {} to {} connections".format(
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
                self.log("Lost connection to {}. Killing...".format(c))
                self.connections.remove(c)
