import asyncio
import sys


MAX_PACKET_SIZE = 1024


class BaseClient():
    _loop = None
    _reader = None
    _writer = None
    finished = False

    def run(self):
        message = 'Hello World!'
        self._loop = asyncio.get_event_loop()
        self._loop.run_until_complete(self.establish_connection(message))
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            pass
        self._loop.close()

    @asyncio.coroutine
    def establish_connection(self, message):
        # Establish the socket
        self._reader, self._writer = yield from asyncio.open_connection(
            '127.0.0.1', 8888, loop=self._loop)

        # TODO: Authentication

        # Send an initial message
        self.send_to_server(message)

        # Schedule the worker task
        asyncio.async(self.receive(), loop=self._loop)
        asyncio.async(self.heartbeat(), loop=self._loop)

    @asyncio.coroutine
    def heartbeat(self):
        while not self.finished:
            self.send_to_server("Heartbeat")
            yield from asyncio.sleep(1.0)

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
            if msg:
                print('Receiving:', msg)

    def send_to_server(self, data):
        print('Sending:', data)
        self._writer.write(data.encode())

    @asyncio.coroutine
    def close(self):
        print("Closing")
        self.finished = True
        self._loop.stop()


###############################################################################


class ClientConnection:
    def __init__(self, r, w):
        self.reader, self.writer = r, w

    def __repr__(self):
        return "<Client {}>".format(self.writer.get_extra_info('peername'))


class BaseAgent():
    """The agent is the secure gateway through which the client connects to
    the full system.

    On one side a secure TCP socket talks to the client, and on the other side
    a Redis pubsub connection speaks with the entire internal network.
    """
    _loop = None
    connections = []
    finished = False

    def run(self):
        self._loop = asyncio.get_event_loop()
        coroutine = asyncio.start_server(
            self.create_client_connection, '127.0.0.1', 8888, loop=self._loop)
        server = self._loop.run_until_complete(coroutine)

        # Serve requests until CTRL+c is pressed
        print('Serving on {}'.format(server.sockets[0].getsockname()))
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            pass

        # Close the server
        server.close()
        self._loop.run_until_complete(server.wait_closed())
        self._loop.close()

    @asyncio.coroutine
    def create_client_connection(self, reader, writer):
        """A unique instance of this coroutine is active for each connected
        client.
        """
        # Keep this connection around for a while
        connection = ClientConnection(reader, writer)
        self.connections.append(connection)
        address = writer.get_extra_info('peername')

        while not self.finished:
            try:
                msg = yield from reader.read(MAX_PACKET_SIZE)
                if not msg:
                    # They've disconnected
                    break
            except (asyncio.CancelledError, asyncio.TimeoutError):
                print("Cancelled or Timeout")
                raise
            except Exception as exc:
                print("Something happened!", exc)
                break
            # Rebroadcast the message to everyone
            if msg:
                print("Received {} from {}".format(msg, address))
                yield from self.broadcast(msg)

        print("Close the client socket for {}".format(address))
        writer.close()
        self.connections.remove(connection)

    @asyncio.coroutine
    def broadcast(self, data):
        print("Sending: {} to {} connections".format(
            data, len(self.connections)))
        for c in self.connections.copy():
            try:
                c.writer.write(data)
                yield from c.writer.drain()
            except ConnectionResetError:
                print("Killing connection to", c)
                self.connections.remove(c)


def main():
    if 'client' in sys.argv:
        c = BaseClient()
        c.run()
    elif 'server' in sys.argv:
        s = BaseAgent()
        s.run()


if __name__ == "__main__":
    main()