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
    ('ping', (
        r"@coffeebot ping",
    )),
    ('love', (
        r"@coffeebot love",
        r"i love you @coffeebot",
    )),
)


def reg_wrap(regex, fmt=r"^.*(?![`'\"]){}(?![`'\"]).*$"):
    """
    Wrap a regex in another, using fmt. Default makes it so
    that any regex quoted does not summon coffeebot, for example demos.

    I should probably make it so that coffeebot never replies to
    itself, regardless.
    """
    return re.compile(fmt.format(regex))


# this is populated by the below function.
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


def where(event_or_context):
    # wheres can be built from a context (a common scenario, since we
    # use wheres as keys for collectives
    if isinstance(event_or_context, Context):
        return Where(context.stream,
                     context.subject)
    message = event_or_context['message']
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


# ==================== Coffeebot, The ====================

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
        self.event_methods = {
            'heartbeat': self.handle_heartbeat,
            'private':   self.handle_private_message,
            'message':   self.handle_public_message,
        }

        # because public messages are the point of interaction, this is
        # another map from parsed directives to methods.
        # each method takes an event, and converts it as needed using the
        # Where/Context utility constructors.
        self.command_methods = {
            'init':   self.init_collective,
            'add':    self.add_to_collective,
            'remove': self.remove_from_collective,
            'ping':   self.ping_collective,
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
        self.collectives = {}

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
        # in all cases I'll want the where and the context
        # if I feed Where a context it should handle that.
        here = Where(event)
        if (here in self.collectives and
                not self.collectives[here].closed):
            # ping the user by name?
            self.public_say(
                """
                pass
                """,
                event)
        else:
            con = Context(event)
            self.collectives[here] = Collective(
                con.user,
                con.stream,
                con.subject)
            self.public_say(
                """
                You've initialized a coffee collective! :tada:
                Wait for others to join, or say `@coffeebot close`
                (without the quotes) to close the collective, randomly
                choose a maker, and have your :coffee:. To join this
                collective, type `@coffeebot yes` in this thread.

                """,
                event)

    def add_to_collective(self, event):
        pass

    def remove_from_collective(self, event):
        pass

    def ping_collective(self, event):
        pass

    def close_collective(self, event):
        # (Feel free to make tea instead, I won't judge. Much.)
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
        """
        Dispatch event based on its type, sending it to the correct handler.
        """
        switch = event['type']
        self.event_methods[switch](event)

    def listen(self):
        self.client.call_on_each_event(
            self.dispatch,
            event_types=self.event_methods.keys())

