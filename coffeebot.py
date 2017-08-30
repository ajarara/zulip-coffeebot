from collections import OrderedDict, namedtuple
from datetime import datetime, timedelta
from random import sample
from os import path
import re

# external dep
import zulip

Directive = namedtuple('Directive', ['command', 'args'])
# type: (str, dict) -> Directive

# a map of regular expressions, all mapped to directives
# we put it in an ordered dict so that we have determinism
# when iterating over it. This means we don't have to worry about
# making our regular expressions mutually exclusive.
# I don't need constant time access (really only need a linked list)
# but there's no reason to clutter this code with an implementation.
_COMMAND_REG_MAP = OrderedDict({
    'init': (
        r"@coffeebot init",
        r"@coffeebot start",
        r"@coffeebot coffee",
    ),
    'add': (
        r"@coffeebot yes",
        r"@coffeebot join",
        r"@coffeebot in",
    ),
    'remove': (
        r"@coffeebot leave",
        r"@coffeebot no",
        r"@coffeebot out",
    ),
    'close': (
        r"@coffeebot done",
        r"@coffeebot close",
        r"@coffeebot stop",
    ),
    'love': (
        r"@coffeebot love",
        r"i love you @coffeebot",
    ),
})


def _reg_wrap(regex, fmt=".*[^`'\"]{}[^`'\"].*"):
    """Wrap a regex in another, using fmt. Default makes it so
    that any regex quoted does not summon coffeebot """
    return re.compile(fmt.format(regex))


_PARSE_CACHE = []


def _generate_parse_map(
        _command_reg_map=_COMMAND_REG_MAP,
        _parse_cache=_PARSE_CACHE):
    """
    Access the parse map. This is a tuple of 2-tuples: regular
    expressions mapped to their commands, to be tried in order. Since
    the reg_map is ordered the result we obtain from this call is
    deterministic, so we cache it in _parse_cache. The first time we
    must generate it.
    """
    if not _parse_cache:
        out = []
        for command, raw_reg_tup in _command_reg_map.items():
            for raw_reg in raw_reg_tup:
                out.append(
                    # wrap the regex in a format and assoc it with command
                    (_reg_wrap(raw_reg), command))
        _parse_cache.append(out)

    return _parse_cache[0]


class Collective():
    def __init__(self, leader, stream, topic, max_size=5, timeout_in_mins=15):
        # TODO: Check max_size and timeout_in_mins for reasonable values
        self.leader = leader
        self.stream = stream
        self.topic = topic
        self.max_size = max_size

        # time invariants
        self.timeout_in_mins = timedelta(minutes=timeout_in_mins)
        self.time_created = datetime.now()

        # self mutable attributes
        self.users = {leader}
        self.closed = False
        self.maker = None

    def close(self):
        if not self.closed:
            if self.users:  # so that we can close an empty coll
                self.elect_maker()
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

    def elect_maker(self):
        if not self.maker:
            self.maker = sample(self.users, 1)
        else:
            raise ValueError("Maker has already been elected!")

    def is_stale(self):
        # this is going to be mocked, waiting 15 minutes for tests to pass
        # is ridiculous, so this should be as simple as possible.
        return datetime.now() - self.time_created >= self.timeout_in_mins

    # ---------- zulip aware/specific functions ----------
    def ping_string(self):
        """
        This is a method that is Zulip aware. The alternative
        is to move this out to Coffeebot which isolates the zulip
        awareness to coffeebot (where it can't be avoided) but
        requires that coffeebot reach into Collectives to act on them.

        Which is less bad is a question I've spent too much time on.
        """
        return " ".join(
            ["@{}".format(user) for user in self.users])

    def timeout_message(self):
        """
        Not a string, but a dict detailing the contents of the message
        and what to send.
        """
        assert self.closed, ("Timeout message retrieved "
                             "without closing collective!")
        return {
            "type": "stream",
            "to": self.stream,
            "subject": self.topic,
            "content": (
                "Coffeebot is impatient and has closed this collective!"
                "The maker coffeebot has chosen is {}\n{}").format(
                    self.maker,
                    self.ping_string(),
                )
        }

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

    def __len__(self):
        return len(self.users)


class Coffeebot():
    """
    Coffeebot's job is to take in requests from the API, attempt to
    execute them in the correct collective. It's coffeebot's job to handle
    exceptional cases like parsing, but the collective's job to notify
    coffeebot about things like adding a user to full collective.
    """
    def __init__(self, stream):
        here = path.abspath(path.dirname(__file__))
        self.client = zulip.Client(
            config_file=path.join(here, "zuliprc.conf"))

        self.curr_collective = None
        self.old_collective = None

    def archive_collective(self):
        self.old_collective = self.curr_collective
        self.curr_collective = None
        # closing the collective elects a maker
        self.old_collective.close()

    def handle_heartbeat(self, event):
        # this is a good opportunity to check if we should close our
        # current collective. Heartbeats are in the v1 API. If this
        # ends up breaking (or heartbeats prove too slow) an
        # alternative implementation is to write a client that listens
        # until a timeout.  or request that the client lib support
        # timeouts. Either works.
        if self.curr_collective and self.curr_collective.is_stale():
            # the collective has timed out. archive it (which closes it)
            self.archive_collective()

            # alert the collective who the maker is.
            self.client.send_message(
                self.old_collective.timeout_message())

    def dispatch_event(self, event):
        print(event)

    def listen(self):
        self.client.call_on_each_event(self.dispatch_event)


def main():
    if zulip.API_VERSTRING != "v1/":
        print("Zulip API client library has changed remote version! Aborting.")
        exit(1)


if __name__ == '__main__':
    main()
