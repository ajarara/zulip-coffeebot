import zulip
from collections import deque, namedtuple
from datetime import datetime, timedelta

# external dependencies
# import asyncio

Directive = namedtuple('Directive', ['command', 'args'])


class Collective():
    def __init__(self, leader, max_size=5, timeout_in_mins=15):
        # TODO: Check max_size and timeout_in_mins for reasonable values
        self.leader = leader
        self.max_size = max_size
        self.timeout_in_mins = timeout_in_mins
        self.time_created = datetime.now()

        # mutable attributes
        self.users = {leader}
        self.closed = False

    def close(self):
        if not self.closed:
            self.closed = True
        else:
            raise ValueError("Collective already closed!")

    def add_user(self, user):
        if not self.closed:
            self.users.add(user)
            if len(self) >= self.max_size:
                self.close()
        else:
            raise KeyError("This collective is closed.")

    def drop_user(self, user):
        if user in self.users:
            if user == self.leader:
                self.leader = None  # :(
            self.users.remove(user)
        else:
            raise KeyError("Member: {} not in the collective".format(user))

    def __len__(self):
        return len(self.users)

    def is_timeout(self):
        pass


class Coffeebot():
    def __init__(self):
        self.collectives = deque()

    def handler(self, message):
        pass
