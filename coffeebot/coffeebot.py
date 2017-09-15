from datetime import datetime, timedelta
from collections import namedtuple
from pprint import pprint
from os import path
import argparse
import random
import re

# external dep
import zulip

# ==================== PARSING ====================

# what are we called?
NAME = "coffeebot"

# coffeebot utilizes this map to understand commands.
# it then maps these commands to actions, and attempts to execute them.
COMMAND_REGS = (
    ('init', (
        "init",
        "start",
        # r"@**coffeebot** coffee",
    )),
    ('add', (
        "yes",
        "join",
        # this is close enough to init that it is worth dropping for now
        # "in(?!i)",
    )),
    ('remove', (
        "no",
        "leave",
        # since this is the inverse of in, not enabled. bad UX otherwise
        # "out",
    )),
    ('state', (
        "state|(?:us)?",
    )),
    ('ping', (
        "ping",
    )),
    ('close', (
        "close",
        "done",
        "stop",
    )),
    ('love', (
        "love",
    )),
)

HELP_STRING = """

Overview:

{0} organizes collectives, groups of people who want coffee. When a collective has enough members, it closes, selecting someone to make coffee for the whole collective.

{0} acts when it is publicly pinged with a command. On private message, {0} replies with this usage string. {0} tries to be as silent as possible, unless there's an exceptional condition. In the ideal case, {0} only sends two messages per collective, an init confirmation and a message at collective close, delegating the coffee maker. Otherwise, for all valid commands, {0} acknowledges the command with :thumbs_up:

Rather than silently drop errors, {0} attempts to explain what went wrong, and suggest a correct request.

Usage:

- "@**{0}** init"

Initialize a collective, with you as the leader. The leader currently has no fancy functionality beyond {0}'s utmost respect.

- "@**{0}** yes"

Join an open collective. By joining you affirm you want coffee, and are willing to make coffee for up to 2 others.

- "@**{0}** no"

Drop your commitment to the collective :disappointed_relieved:. You renounce your claim to coffee, and thus don't have to risk making it. Once a collective is closed, you cannot leave it.

- "@**{0}** close"

Close the collective. Only those within it may close it.

- "@**{0}** ping"

Ping all those in the collective (this should only be used to signify coffee is ready, as that's what {0} indicates). Only the maker may do this, but there's nothing stopping someone from pinging everyone manually.

- "@**{0}** state"

Publicly say the state of the collective. This includes the members inside, the time the collective was created, and the approximate time left until the collective timeouts.


Questions? Bugs? Message @**Ahmad Jarara (S2'17)** or seek the source: https://github.com/alphor/zulip-coffeebot
""".format(NAME.capitalize())  # noqa: E501


# soon enough I should move the default format to a more readable reg
def reg_wrap(regex, fmt=r"^.*(?![`'\"])@\*\*{}\*\*\s+{}(?![`'\"]).*$",
             name=NAME):
    """
    Wrap a regex in another, using fmt. Default makes it so
    that any regex quoted does not summon coffeebot, for example demos.
    """
    return re.compile(fmt.format(name, regex))


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
    downcased_by_line = message.lower().split(sep="\n")
    for reg, command in get_parse_map():
        for line in downcased_by_line:
            if reg.match(line):
                return command


# ==================== Coffeebot primitives ====================

# each action concerning coffeebot has a context. Contexts are simple!
Context = namedtuple("Context", ['stream', 'subject', 'user'])


# we can make contexts from zulip events!
def make_context(event):
    message = event['message']
    return Context(message['display_recipient'],
                   message['subject'],
                   message['sender_full_name'])


# Collectives are identified by where they are, so we'll need that too.
Where = namedtuple("Where", ['stream', 'subject'])


def make_where(event_or_context):
    # wheres can be built from a context (a common scenario, since we
    # often need context to determine if a where is necessary)
    # primary usage of wheres are to identify collectives
    if isinstance(event_or_context, Context):
        return Where(event_or_context.stream,
                     event_or_context.subject)
    message = event_or_context['message']
    return Where(message['display_recipient'],
                 message['subject'])


class Collective():
    """
    Collectives are groups of people interested in making coffee.
    """
    def __init__(self, leader, max_size=3, timeout_in_mins=15):
        # TODO: Check max_size and timeout_in_mins for reasonable values
        # when arguments are exposed
        self.leader = leader
        self.max_size = max_size

        self.timeout_in_mins = timedelta(minutes=timeout_in_mins)
        self.time_created = datetime.now()

        # mutable attributes
        self.users = {leader}
        self.closed = False
        self.maker = None

    # ==================== collective actions ====================
    def elect_maker(self):
        assert not self.maker
        self.maker = random.choice(list(self.users))

    def close(self):
        assert not self.closed
        if self.users:
            self.elect_maker()
        self.closed = True

    # ==================== forwarding methods ====================
    def add(self, user):
        self.users.add(user)

    def remove(self, user):
        self.users.remove(user)

    def __contains__(self, user):
        return user in self.users

    def __len__(self):
        return len(self.users)

    # ==================== state representation ====================
    def is_stale(self):
        return datetime.now() - self.time_created >= self.timeout_in_mins

    def ping_string(self):
        # this should only be accessed when closed.
        assert self.closed
        return " ".join(
            ["@**{}**".format(user) for user in self.users])

    def __repr__(self):
        out = []
        out.append("Members: {}".format(
            ", ".join(self.users)))
        out.append("Positions left: {}".format(
            self.max_size - len(self.users)))
        out.append("Time created: {:%A, %I:%M:%S %p}".format(
            self.time_created))
        if self.closed:
            out.append("Status: Closed")
        else:
            # this part makes me sad.
            minutes_left = int(
                (self.timeout_in_mins -
                 (datetime.now() - self.time_created)).seconds / 60)
            if minutes_left == 0:
                out.append("Status: Closing soon!")
            else:
                out.append("Until timeout: {} minutes".format(minutes_left))
        return "\n".join(out)


# ==================== Coffeebot, The ====================


class Coffeebot():
    """
    Coffeebot's job is to take in requests from the API and attempt to
    execute them in the correct collective.
    """
    def __init__(self, config=None, name=NAME,
                 help_string=HELP_STRING):

        # because public messages are the point of interaction, this is
        # a map from parsed directives to methods.
        # each method takes an event, and converts it as needed using the
        # Where/Context utility constructors.
        self.command_methods = {
            'init':   self.init_collective,
            'add':    self.add_to_collective,
            'remove': self.remove_from_collective,
            'state':  self.state_of_collective,
            'ping':   self.ping_collective,
            'close':  self.close_collective,
            'love':   self.candy_cane,
        }

        self.help_string = help_string

        if isinstance(config, dict):
            self.client = zulip.Client(**config)
        elif isinstance(config, str):
            self.client = zulip.Client(config_file=config)

        # besides IO, this is the only state in Coffeebot.
        self.collectives = {}

    # ==================== API ====================
    def public_say(self, content, where):
        """
        >>> isinstance(where, Where)
        True
        """
        self.client.send_message({
            "type": "stream",
            "to": where.stream,
            "subject": where.subject,
            "content": content,
        })

    # we always send a help_string, independent of context.
    def private_say(self, event):
        message = event['message']
        self.client.send_message({
            "type": "private",
            "to": message['sender_email'],
            "content": self.help_string,
        })

    # not available in the zulip API.
    def emoji_reply(self, emoji, event):
        msg = event['message']['id']
        self.client.call_endpoint(
            "messages/{}/emoji_reactions/{}".format(
                msg, emoji),
            method='PUT')

    # ==================== utility ====================
    def is_bot_message(self, event):
        sender_email = event['message']['sender_email']
        # currently all bots have "-bot@" in their email, at least on
        # Recurses realm.  since this is itself a bot, the second
        # condition alone is enough but this is kept in here in the
        # case where this policy differs by realm
        return self.client.email == sender_email or "-bot@" in sender_email

    # ==================== collective interaction ====================
    def init_collective(self, event):
        con = make_context(event)
        here = make_where(con)
        if (here in self.collectives and
                not self.collectives[here].closed):
            # ping the user by name? let's not.
            # these are a little too verbose I think.
            self.public_say(
                ("The collective in this thread is still open. If you'd "
                 "like, join this one with \"@**coffeebot** yes\" or "
                 "start your own in some other thread."),
                here)
        else:
            new_coll = Collective(con.user)
            self.collectives[here] = new_coll
            self.public_say(
                ("You've initialized a coffee collective! :tada:\n\n "
                 "This collective can take {} other members (you can join by "
                 "typing \"@**coffeebot** yes\" or \"@**coffeebot** join\"). "
                 "For more usage details, send me a private message.").format(
                     new_coll.max_size - 1),
                here)

    def add_to_collective(self, event):
        con = make_context(event)
        here = make_where(con)
        if here in self.collectives:
            coll = self.collectives[here]
            if coll.closed:
                self.public_say(
                    # notify user of all open collectives?
                    ("This collective is closed.  Start your own with "
                     "\"@**coffeebot** init\" \n\nFor further details, "
                     "send me a private message."), event)
            elif con.user in coll.users:
                self.public_say(
                    ("You're already in this collective. Coffeebot "
                     "appreciates the enthusiasm, though."),
                    here)
            else:
                coll.add(con.user)
                self.emoji_reply("thumbs_up", event)
        else:
            self.public_say(
                ("There is no recently active collective in this "
                 "thread. Make a new one with \"@**coffeebot** init\"! "
                 "\n\nFor further details, send me a private message."),
                here)

    def remove_from_collective(self, event):
        con = make_context(event)
        here = make_where(con)
        if here in self.collectives:
            coll = self.collectives[here]
            if coll.closed:
                self.public_say(
                    ("No one can leave a closed collective. "
                     "You are free to forfeit your coffee "
                     "of course, just let the coffee maker, {}, know").format(
                         coll.maker),
                    here)
            elif con.user in coll:
                coll.remove(con.user)
                self.emoji_reply("thumbs_up", event)
                if len(coll) == 0:
                    coll.close()
                    self.public_say(
                        ("Since everyone has left this collective, "
                         "it is now closed."),
                        here)

    def state_of_collective(self, event):
        here = make_where(event)
        if here in self.collectives:
            self.public_say(
                repr(self.collectives[here]),
                here)
        else:
            self.public_say(
                ("Coffeebot does not know anything about the collectives "
                 "in this thread. Coffeebot has no persistent storage. :cry:"),
                here)

    def ping_collective(self, event):
        con = make_context(event)
        here = make_where(con)

        if here in self.collectives:
            coll = self.collectives[here]
            if coll.closed:
                if coll.maker == con.user:
                    self.public_say(
                        "**Coffee is ready!**\n\n {}".format(
                            coll.ping_string()),
                        here)
                else:
                    self.public_say(
                        "Only {} (the coffee maker) may ping.".format(
                            coll.maker),
                        here)
            else:
                # eh I could see how this could be annoying
                # if you're in a rush or something.
                self.public_say(
                    ("This collective isn't closed yet, "
                     "so Coffeebot sees no reason to ping it."),
                    here)

    def close_collective(self, event):
        con = make_context(event)
        here = make_where(con)
        if here in self.collectives:
            coll = self.collectives[here]
            if coll.closed:
                self.public_say(
                    "This collective is already closed!",
                    here)
            elif con.user in coll:
                coll.close()
                self.public_say(
                    ("Coffeebot has deliberated for almost {} μs "
                     "and has chosen @**{}** as the coffee maker.\n\nOnce you "
                     "are done making coffee, ping the members of this "
                     "collective with \"@**coffeebot** ping\" in this "
                     "thread.").format(
                         str(random.random())[:6],
                         coll.maker),
                    here)

    # you go glenn coco
    def candy_cane(self, event, _det=None):
        possibilities = ('message', 'emoji')

        if _det in possibilities:
            action = _det
        else:
            action = random.choice(['message', 'emoji'])

        if action == 'emoji':
            num_emoji = random.randint(1, 7)
            emoji = random.sample(
                [valid_emoji for valid_emoji in CANES
                 if valid_emoji.startswith(":")],
                num_emoji)
            for e in emoji:
                self.emoji_reply(e, event)
        elif action == 'message':
            # love strings are defined below
            self.public_say(random.choice(CANES), event)

    # ==================== dispatch ====================
    def handle_heartbeat(self, beat):
        for here, coll in self.collectives.items():
            if coll.is_stale() and not coll.closed:
                # timeout has occured
                coll.close()
                self.public_say(
                    ("This collective has timed out. Coffeebot has chosen "
                     "@**{}** as the maker.\n\nOnce you are done making "
                     "coffee, ping the members of this collective "
                     "with \"@**coffeebot ping**\"").format(coll.maker),
                    here)

    def handle_private_message(self, event):
        """
        For now, pass along the event to private_say, which'll send a
        help string.

        Coffeebot doesn't do insider coffee making.
        """
        self.private_say(event)

    def handle_public_message(self, event):
        message = event['message']
        if message['is_mentioned']:
            command = parse(message['content'])

            if not command:
                here = make_where(event)
                self.public_say(
                    ("This request wasn't understood. "
                     "Message me for usage details."),
                    here)
            else:
                self.command_methods[command](event)

    def dispatch(self, event):
        """
        Dispatch event based on its type, sending it to the correct handler.
        """
        switch = event['type']
        print("Obtained event: {}".format(event))
        if switch == 'heartbeat':
            self.handle_heartbeat(event)

        # never reply to thyself, or other bots.
        elif switch == 'message' and not self.is_bot_message(event):
            kind = event['message']['type']
            if kind == 'private':
                self.handle_private_message(event)
            elif kind == 'stream':
                self.handle_public_message(event)

    def listen(self):
        self.client.call_on_each_event(
            self.dispatch,
            # 'reaction' planned but not currently supported
            event_types=['heartbeat', 'message'])


CANES = {
    ("    \\o/\n"
     "     |\n"
     "    /_\\"),
    ":heart:",
    ":hearts",
    ":yellow_heart:",
    ":green_heart:",
    ":blue_heart:",
    ":two_hearts:",
    ":revolving_hearts:",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Runtime configuration for Coffeebot")

    parser.add_argument('--api_key', metavar='s0meAP1key', type=str, nargs='?')
    parser.add_argument('--email', metavar='coffeebot-bot@$REALM',
                        type=str, nargs='?')
    parser.add_argument('--site', metavar='recurse.zulipchat.com',
                        type=str, nargs='?')
    parser.add_argument('--config_file', metavar='zuliprc.conf',
                        type=str, nargs='?')
    args = parser.parse_args()

    if args.api_key and args.email and args.site:
        c = Coffeebot(config={
            'api_key': args.api_key,
            'email':   args.email,
            'site':    args.site,
        })
    elif args.api_key or args.email or args.site:
        print(("api_key, email, and site are all mutually required."
               "\n You entered:\n{}").format(pprint(args)))
        exit(1)
    elif args.config_file:
        # string
        c = Coffeebot(config=args.config_file)
    else:
        # default
        here = path.abspath(path.dirname(__file__))
        config_file = path.join(here, "zuliprc.conf")
        c = Coffeebot(config=config_file)
    c.listen()


if __name__ == '__main__':
    main()
