from datetime import datetime, timedelta
from collections import namedtuple
from random import sample
from os import path
import re

# external dep
import zulip

Directive = namedtuple('Directive', ['command', 'args'])
# type: (str, dict) -> Directive

# an association tuple of directives to regular expressions.
# this is used to build the inverse association list,
# this isn't used beyond generating the parse cache

# note the raw string prefix. It doesn't matter here (it would if
# there were backslashes), but in case I'd like to extend these regs
# later on it makes things look nicer.

# since we're just starting, make the input range small
_COMMAND_REGS = (
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


def _reg_wrap(regex, fmt=r"^.*(?![`'\"]){}(?![`'\"]).*$"):
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


def _get_parse_map(
        _command_regs=_COMMAND_REGS,
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
    if _command_regs not in _parse_cache:
        out = []
        for command, raw_reg_tup in _command_regs:
            for raw_reg in raw_reg_tup:
                out.append(
                    # wrap the regex in a format and assoc it with command
                    (_reg_wrap(raw_reg), command))
        _parse_cache[_command_regs] = out

    return _parse_cache[_command_regs]


def _parse(message):
    """
    Given a message, return the first match obtained from
    _get_parse_map. If no matches are obtained return None.
    """
    downcased = message.lower()
    for reg, command in _get_parse_map():
        if reg.match(downcased):
            return command


# I only catch CoffeeErrors. If theres a legit ValueError
# I'd like to know about it in the logs
class CoffeeError(ValueError): pass  # noqa: E701


# the only stream I want to interact with is #coffee, so we'll hard code this.
# the alternative is to lookup the stream_id at message time which is
# more complicated.
COFFEEBOT_STREAM = ["#coffee"]


# assumes event is a public message with a topic associated with it
# returns a dict that can be fed into a zulip client send_message.
# this makes it easy to change the hardcoded value later on.
def _format_response(event, content):
    return {
        "type": "stream",
        "to": COFFEEBOT_STREAM,
        "subject": event['subject'],
        "content": content,
    }


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
            raise CoffeeError("This collective has already been closed.")

    def add(self, user):
        if not self.closed:
            self.users.add(user)
            if len(self) >= self.max_size:
                self.close()
        else:
            raise CoffeeError(
                ("Add: Cannot add {}, this collective "
                 "is already closed.").format(user))

    def remove(self, user):
        if user in self.users:
            if user == self.leader:
                self.leader = None  # :(
            self.users.remove(user)
        else:
            raise CoffeeError(
                ("Remove: {} is not in "
                 "the collective!").format(user))

    def elect_maker(self):
        if not self.maker:
            # sample returns a list. get the first.
            self.maker = sample(self.users, 1)[0]
        else:
            # this isn't user exposed, so if this breaks we want to
            # know about it
            raise RuntimeError(
                """
                Elect_maker called on already formed collective:
                  Stream: {}
                  Topic: {}
                  Time: {}
                """.format(self.stream,
                           self.topic,
                           datetime.now().isoformat()))

    def is_stale(self):
        # this is going to be mocked, waiting 15 minutes for tests to pass
        # is ridiculous, so this should be as simple as possible.
        return datetime.now() - self.time_created >= self.timeout_in_mins

    # ---------- zulip aware/specific functions ----------
    def ping_string(self):
        """
        Not the biggest fan of Zulip aware collective methods. The
        alternative is to move this out to Coffeebot which isolates
        the zulip awareness to coffeebot (where it can't be avoided)
        but requires that coffeebot reach into Collectives to act on
        them.

        Which is less bad is a question I've spent too much time on.
        """
        return " ".join(
            ["@**{}**".format(user) for user in self.users])

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

    A design goal that is kind of broken here is to have as little
    logic as possible inside of coffeebot. Since we're interfacing
    directly with an API, most actions are stateful, which makes
    testing this logic a little more involved then testing something
    like a collective.
    """
    def __init__(self, stream, config_file="zuliprc.conf"):
        here = path.abspath(path.dirname(__file__))
        # used by self.dispatch and self.listen. maps events to handlers
        # this technically could be class level but it provides for a
        # weird interface.
        self.event_method_map = {
            'heartbeat': self.handle_heartbeat,
            'private': self.handle_private_message,
            'message': self.handle_public_message,
        }

        if config_file:
            self.client = zulip.Client(
                config_file=path.join(here, config_file))
        else:
            # we're testing, and don't want to accidentally post.
            self.client = None

        # mutable attributes
        self.curr_collective = None
        self.old_collective = None

    def archive_collective(self):
        self.old_collective = self.curr_collective
        self.curr_collective = None
        # closing the collective elects a maker
        self.old_collective.close()

    # hmm so maybe this is the wrong way to go about this.
    def handle_heartbeat(self, _):
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
            self.client.send_message({
                "type": "stream",
                "to": self.old_collective.stream,
                "subject": self.old_collective.topic,
                "content": self.old_collective.timeout_message()
            })

    def handle_private_message(self, event):
        self.client.send_message({
            "type": "private",
            "to": event.sender_email,
            # should be help string, instead.
            "content": ("I don't do insider coffee making. "
                        # publically? I always have to check.
                        "Ping me publicly.")
            })

    def handle_public_message(self, event):
        """
        TODO: Attempt to parse the message contents, if mentioned. If
        nothing is found, send an error message, maybe tell user to PM
        coffeebot? Otherwise,dispatch the directive on the current collective.

        Hmm. If it's a ping then it should act on the closed
        collective.

        That's a little confusing, as it'll do this even if the user
        does it in a different stream.  Maybe putting collectives in a
        deque is a good idea. During heartbeats check for stale
        collectives and collectives that are expired (beyond two
        hours), closing the first and removing the second.

        This could be done easily by putting all collectives in a
        deque. For the second case, do something like while colls and
        colls[0].is_moldy(): colls.leftpop

        For the first, iterate backwards through the deque, attempting
        to close all collectives that are stale until you hit a
        CoffeeError.

        This is certainly going to be the roughest part of coffeebot.
        """
        # never reply to myself:
        if not event['message']['is_me_message']:
            if event['message']['is_mentioned']:
                command = _parse(event['content'])
                if command is None:
                    # coffeebot doesn't recognize this string
                    self.client.send_message(
                        _format_response(
                            event,
                            ("I can't figure out what you mean.\n"
                             "Private message me for help please.")
                            )
                    )
                elif command == 'init':
                    # eh... this should be its own function.
                    if self.curr_collective:
                        self.client.send_message(
                            _format_response(
                                event,
                                ("There is a collective currently open in"
                                 " {}. Join that one please.").format(
                                     self.curr_collective.topic)))
                    else:
                        self.curr_collective = Collective(
                            event['message']['sender_full_name'],
                            COFFEEBOT_STREAM,
                            event['subject'])
                elif command == 'ping':
                    # this should absolutely be its own function.
                    # the number of things that could go wrong here are
                    # very high.
                    if self.old_collective:
                        pass  # TODO
                else:
                    try:
                        # TODO: command needs to be put into a directive
                        # and be supplied with arguments.
                        self.curr_collective.dispatch(command)
                    except CoffeeError as e:
                        self.client.send_message(
                            _format_response(event,
                                             e.args[0])
                            )

    def _help_string(self):
        """
        This is done on error, or on private message. Should relay version,
        """
        pass

    def dispatch_event(self, event):
        "Dispatch on event['type'], passing event to m "
        switch = event['type']
        # dispatch on switch, passing event to the method
        self.event_method_map[switch](event)

    def listen(self):
        # would a runtime error propogate through a blocking call?
        # can't know until it happens.
        try:
            self.client.call_on_each_event(
                self.dispatch_event,
                event_types=self.event_method_map.keys()
            )
        except RuntimeError as e:
            # relay that something went terribly wrong inside coffeebot
            # since we can't tell rn which one it was, just tell current_coll
            self.client.send_message({
                "type": "stream",
                "to": curr_collective.stream,
                "subject": curr_collective.topic,
                "content": ("Something has gone very wrong. "
                            "Pinging **@Ahmad Jarara**")})


def main():
    if zulip.API_VERSTRING != "v1/":
        print("Zulip API client library has changed remote version! Aborting.")
        exit(1)


if __name__ == '__main__':
    main()
