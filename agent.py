# coding=utf-8
"""The Agent is responsible for being the gateway between the internal servers
and the external clients. Because of this it also is responsible for enforcing
permissions and authentication.
"""

import asyncio
import json

from base import InternalMessagingServer
from settings import MAX_PACKET_SIZE
from util import Channel


class ClientConnection:
    """Represents all the data pertaining to one client."""
    def __init__(self, r, w):
        # The client connection should not read or write data if it has no id
        # (except for authentication)
        self.id = None
        self.reader, self.writer = r, w
        self.subscriptions = []

    def responds_to(self, channel: Channel) -> bool:
        """Return whether or not the client is listening to this channel."""
        # I always am interested in myself
        if channel.target == self.id:
            return True
        # Otherwise I just check my zone subscriptions
        return channel.target in self.subscriptions

    def kick(self):
        """Terminate this client connection."""
        pass  # TODO: Implement me! We need an easy way to kick a client.

    def __repr__(self):
        host, port = self.writer.get_extra_info('peername')
        return "<Client {}:{}>".format(host, port)


class PastryAgent(InternalMessagingServer):
    """The agent is the secure gateway through which the client connects to
    the full system.

    On one side a secure TCP socket talks to the client, and on the other side
    a Redis pubsub connection speaks with the entire internal network.
    """
    _loop = None
    connections = []
    finished = False

    async def _authenticate(self, connection: ClientConnection) -> str:
        """Validate credentials and return the client id."""
        # Wait for the client to send credentials
        self.log("Waiting for authentication from", connection)
        data = await connection.reader.readline()
        credentials = json.loads(data.decode())

        # Let the subclass decide if this the credentials are valid
        client_id = await self.validate_credentials(credentials)

        # Send the client its new id
        connection.writer.write(str(client_id).encode() + b'\n')
        return str(client_id)

    async def validate_credentials(self, credentials: dict) -> str:
        """To be overridden by the subclass"""
        raise NotImplementedError()

    def startup(self):
        """Run the server loop and begin accepting connections."""
        # TODO: Move host:port to an argument?
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

    async def _create_client_connection(self, reader, writer):
        """A unique instance of this coroutine is active for each connected
        client.
        """
        # Keep this connection around for a while
        connection = ClientConnection(reader, writer)
        self.connections.append(connection)

        # TODO: Finish authentication process
        client_id = await self._authenticate(connection)
        if not client_id:
            self.finished = True
        connection.id = client_id

        # Sign up for internal private messages for this user
        self.internal_subscribe(connection.id)

        while not self.finished:
            try:
                msg = await reader.read(MAX_PACKET_SIZE)
                if not msg:  # They've disconnected
                    break
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self.log("Cancelled or Timeout")
                raise
            except Exception as exc:
                self.log("Something happened!", exc)
                break
            # Handle the message
            await self._read_message(connection, msg)

        # Cleanup
        self.log("Close the socket for {}".format(connection))
        writer.close()
        # Tell all relevant servers that the client has left
        for zone in connection.subscriptions:
            channel = Channel(target=zone, method="leave")
            self.internal_broadcast(channel, connection.id)
        self.internal_unsubscribe(connection.id)
        self.connections.remove(connection)

    async def _read_message(self, sender: ClientConnection, data: bytes):
        for d in [_ for _ in data.split(b'\n') if _]:
            # Decode the message
            raw_message = d.decode('utf8')

            input_channel, message = raw_message.split("|")
            channel = Channel.parse(input_channel)

            # Join requests
            if channel.method == 'join':
                # TODO: Hang up on any requests that aren't permitted
                # TODO: (ie. can't subscribe to any subchannels: no `.`s)
                # TODO: Also some channels are restricted to internal usage
                # TODO: Can we reject subscriptions to unknown zones?
                # TODO: Can ONLY subscribe to zones
                self.log("Joining", sender, "to", channel.target)
                sender.subscriptions.append(channel.target)
                self.internal_subscribe(channel.target)
                # Trigger the sync the state of the subscription
                self.internal_broadcast(channel, sender.id)
            # Leave request. No permission necessary.
            elif channel.method == 'leave':
                self.log("Removing", sender, "from", d)
                # TODO: Don't crash if it's not in the list
                sender.subscriptions.remove(channel.target)
                # TODO: Check all subscriptions to see if this is needed any
                # more. Others are probably still using it!
                self.internal_unsubscribe(channel.target)
                # TODO: Trigger a delete state for the leaver
                self.internal_broadcast(channel, sender.id)
            else:
                self.log("Some other message", sender, "from", d)
                # This is a non-pubsub message; forward to the do handler
                await self._handle_client_message(sender, channel, message)

    async def _handle_client_message(self, sender: ClientConnection,
                                     channel: Channel, message: str):
        # TODO: Why async?
        # TODO: This should receive channels too?
        # Subscription requests are already handled; must be a
        # DistributedObject create/update/delete/call.
        # TODO: Check that the message is permitted; if not, kill.
        self.log("Received {} from {}".format(channel, sender))
        # Once we know the message is allowed, send it to the zone server
        # TODO: Creating objects on the client here. Probably need the client
        # to send channel data too

        # Handle an update message
        # TODO: Need to validate stuff
        # kwargs = json.loads(message)
        self.internal_broadcast(channel, message)

    def _handle_internal_message(self, channel, message):
        """Whenever the agent receives an internal message, it's forwarded
        to all relevant clients.
        """
        asyncio.ensure_future(self.client_broadcast(channel, message),
                              loop=self._loop)

    async def client_broadcast(self, channel: Channel, data: str):
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
                await c.writer.drain()
            except ConnectionResetError:
                self.log("Lost connection to {}. Killing...".format(c))
                self.connections.remove(c)
