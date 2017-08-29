import zulip
from collections import deque, namedtuple
from datetime import datetime, timedelta


Directive = namedtuple('Directive', ['command', 'args'])
# type: (str, dict) -> Directive


class Collective():
    def __init__(self, leader, stream, max_size=5, timeout_in_mins=15):
        # TODO: Check max_size and timeout_in_mins for reasonable values
        self.leader = leader
        self.stream = stream
        self.max_size = max_size
        self.timeout_in_mins = timeout_in_mins
        self.time_created = datetime.now()

        # self mutable attributes
        self.users = {leader}
        self.closed = False

    def close(self):
        if not self.closed:
            self.closed = True
        else:
            raise ValueError("This collective has already been closed.")

    def add(self, user):
        if not self.closed:
            self.users.add(user)
            if len(self) >= self.max_size:
                self.close()
        else:
            raise ValueError("This collective is closed.")

    def remove(self, user):
        if user in self.users:
            if user == self.leader:
                self.leader = None  # :(
            self.users.remove(user)
        else:
            raise ValueError("{} is not in the collective!".format(user))

    def __len__(self):
        return len(self.users)

    def dispatch(self, directive):
        """
        Take a directive, map it to a function, execute it. Do no error checks.
        """
        func = {
            "add": self.add,
            "remove": self.remove,
            "close": self.close,
        }[directive.command]

        if directive.args:
            func(directive.args)
        else:
            func()


class Coffeebot():
    """
    Coffeebot's job is to take in requests from the API, attempt to
    execute them in the correct collective, If the collective emanates
    an error, present it reasonably to the thing initiating the request.
    """
    def __init__(self):
        self.collectives = deque()

    def parse(self, message):
        pass

    def listen(self):
        pass

    def handle(self, message):
        pass
