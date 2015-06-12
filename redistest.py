import redis
import asyncio
import signal

r = redis.StrictRedis(host='localhost', port=6379, db=0)

p = r.pubsub()
p.psubscribe('zone-1.*')

r.publish('my-first-channel', 'some data')
r.publish('zone-1.avatar.create', '{"name": "foo"}')


def kickstart():
    message = p.get_message()
    if message:
        print(message)
    loop = asyncio.get_event_loop()
    loop.call_soon(kickstart)


def main():
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.add_signal_handler(signal.SIGTERM, loop.stop)
    loop.call_soon(kickstart)
    loop.run_forever()


if __name__ == "__main__":
    main()