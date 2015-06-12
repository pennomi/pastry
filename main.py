"""
Pastry is a DistributedObject architecture that makes creating MMO games easy as pie!
"""
import sys
from base import DistributedObject, AI, Client, StateServer


class DistributedPerson(DistributedObject):
    first_name = ""
    last_name = ""
    age = 0

    @property
    def name(self):
        return "{} {}".format(self.first_name, self.last_name)


class MyClient(Client):
    def __init__(self):
        super().__init__()
        self.register_channel("zone-1")
        self.register_channel("zone-2")


class MyAI(AI):
    def __init__(self):
        super().__init__()
        bill = DistributedPerson(first_name="Bill", last_name="Kerman", age=1)
        self.create_object(bill)
        bill.save()


if __name__ == "__main__":
    thing = sys.argv[1]  # python main.py FOO
    if thing == 'server':
        to_start = StateServer()
    elif thing == 'client':
        to_start = MyClient()
    elif thing == 'ai':
        to_start = MyAI()
    else:
        raise ValueError('Must be server, client or ai')
    to_start.run()