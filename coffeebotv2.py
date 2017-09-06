from datetime import datetime, timedelta
from collections import namedtuple
from random import sample
from os import path
import re

# external dep
import zulip

# ==================== PARSING ====================
COMMAND_REGS = (
    ('init', (
        r"@coffeebot init",
        r"@coffeebot start",
        # r"@coffeebot coffee",
    )),
    ('add', (
        r"@coffeebot yes",
        r"@coffeebot join",
        # this is close enough to init that it is worth dropping for now
        # r"@coffeebot in(?!i)",
    )),
    ('remove', (
        r"@coffeebot no",
        r"@coffeebot leave",
        # since this is the inverse of in, not enabled. bad UX otherwise
        # r"@coffeebot out",
    )),
    ('close', (
        r"@coffeebot done",
        r"@coffeebot close",
        r"@coffeebot stop",
    )),
    ('love', (
        r"@coffeebot love",
        r"i love you @coffeebot",
    )),
)

# "Here's some conversation, but @coffeebot init it's only mildy
# relevant to this bot"


def reg_wrap(regex, fmt=r"^.*(?![`'\"]){}(?![`'\"]).*$"):
    """
    Wrap a regex in another, using fmt. Default makes it so
    that any regex quoted does not summon coffeebot, for example demos.
    
    I should probably make it so that coffeebot never replies to
    itself, regardless.
    """
    return re.compile(fmt.format(regex))


# this is populated by the below function. Don't think of it as a
# list, think of it as a container.
_PARSE_CACHE = {}


def get_parse_map(
        command_regs=COMMAND_REGS,
        _parse_cache=_PARSE_CACHE):
    """
    Access the parse map. This is a tuple of 2-tuples: regular
    expressions mapped to their commands, to be tried in order. Since
    the reg_map is ordered the result we obtain from this call is
    deterministic, so we cache it in _parse_cache. The first time we
    must generate it.

    Returns something like this:
      ((re.compile('.*[^`'\"]@coffeebot init[^`'\"].*'), 'init'),
       (re.compile('.*[^`'\"]@coffeebot no[^`'\"].*'), 'remove')
       # etc.
      )
    """
    if command_regs not in _parse_cache:
        out = []
        for command, raw_reg_tup in command_regs:
            for raw_reg in raw_reg_tup:
                out.append(
                    # wrap the regex in a format and assoc it with command
                    (reg_wrap(raw_reg), command))
        _parse_cache[command_regs] = out

    return _parse_cache[command_regs]


def parse(message):
    """
    Given a message, return the first match obtained from
    get_parse_map. If no matches are obtained return None.
    """
    downcased = message.lower()
    for reg, command in get_parse_map():
        if reg.match(downcased):
            return command


# ==================== Coffeebot primitives ====================

# each action concerning coffeebot has a context. Contexts are simple!
Context = namedtuple("Context", ['stream', 'subject', 'user'])


# we can make contexts from zulip events!
def context(event):
    message = event['message']
    return Context(message['display_recipient'],
                   message['subject'],
                   message['sender_full_name'])


# Collectives are identified by where they are, so we'll need that too.
Where = namedtuple("Where", ['stream', 'subject'])


def where(event):
    message = event['message']
    return Where(message['display_recipient'],
                 message['subject'])


# collectives are just mutable data structures that coffeebot acts on.
# they can't have the context to understand what to do in all
# situations, so rather than implement half of their actions here and
# half of their actions in coffeebot, this will just be a fancy dict that
# coffeebot reaches into and manipulates.
class Collective():
    def __init__(self, leader, stream, subject,
                 max_size=5, timeout_in_mins=15):
        # TODO: Check max_size and timeout_in_mins for reasonable values
        self.leader = leader
        self.stream = stream
        self.subject = subject
        self.max_size = max_size

        self.timeout_in_mins = timedelta(minutes=timeout_in_mins)
        self.time_created = datetime.now()

        # mutable attributes
        self.users = {leader}
        self.closed = False
        self.maker = None

    # the notable exceptions are for convenient methods to represent state
    def is_stale(self):
        return datetime.now() - self.time_created >= self.timeout_in_mins

    def ping_string(self):
        # this should only be accessed when closed.
        assert self.closed
        return " ".join(
            ["@**{}**".format(user) for user in self.users])

    def __len__(self):
        return len(self.users)


class Coffeebot():
    """
    Coffeebot's job is to take in requests from the API and attempt to
    execute them in the correct collective.
    """
    def __init__(self, stream, config_file="zuliprc.conf"):
        here = path.abspath(path.dirname(__file__))
        # used by self.dispatch and self.listen. maps events to handlers
        # this technically could be class level but it provides for a
        # weird interface.
        self.event_method_map = {
            'heartbeat': self.handle_heartbeat,
            'private':   self.handle_private_message,
            'message':   self.handle_public_message,
        }

        # because public messages are the point of interaction, this is
        # another map from parsed directives to methods.
        # each method takes an event, and converts it as needed using the
        # Where/Context utility constructors.
        self.command_method_map = {
            'init':   self.init_collective,
            'add':    self.add_to_collective,
            'remove': self.remove_from_collective,
            'close':  self.close_collective,
            'love':   self.candy_cane,
        }

        # TODO
        self.help_string = """
            pass
        """
        self.client = zulip.Client(
            config_file=path.join(here, config_file))

        # besides IO, this is the only state in Coffeebot.
        self.bag_collectives = {}

    # ==================== utility ====================
    def public_say(self, content, event):
        here = Where(event)
        self.client.send_message({
            "type": "stream",
            "to": here.stream,
            "subject": here.subject,
            "content": content,
        })

    # ==================== collective interaction ====================
    def init_collective(self, event):
        pass

    def add_to_collective(self, event):
        pass

    def remove_from_collective(self, event):
        pass

    def close_collective(self, event):
        pass

    def candy_cane(self, event):
        pass

    # ==================== dispatch ====================
    def handle_heartbeat(self, beat):
        pass

    def handle_private_message(self, event):
        pass

    def handle_public_message(self, event):
        pass

    def dispatch(self, event):
        pass

    def listen(self):
        self.client.call_on_each_event(
            self.dispatch,
            event_types=self.event_method_map.keys())

