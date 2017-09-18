from coffeebot.coffeebot import parse, make_where, make_context
from coffeebot.coffeebot import Where, Context, Collective, Coffeebot
from coffeebot.coffeebot import NAME

from collections import namedtuple

from hypothesis import given
from hypothesis.strategies import from_regex, text

import pytest

def test_correct():
    assert True

@given(text())
def test_hypothesis(s):
    def ref(x):
        return x
    assert s == ref(s)


# ==================== parsing ====================

@given(text(), text())
def test_parse(s1, s2):
    phrases = (" @**coffeebot** init ",
               " @**coffeebot** join ",
               " @**coffeebot** no ",
               " @**coffeebot** ping ")
    for ph in phrases:
        assert parse(s1 + ph + s2)


# ==================== utility classes ====================

def make_event(display_recipient, subject, sender_full_name):
    return {
        'message': {
            'display_recipient': display_recipient,
            'subject': subject,
            'sender_full_name': sender_full_name,
        },
    }


@given(text(), text(), text())
def test_context(display_recipient, subject, sender_full_name):
    event = make_event(display_recipient, subject, sender_full_name)
    assert isinstance(make_context(event), Context)


@given(text(), text(), text())
def test_where(display_recipient, subject, sender_full_name):
    event = make_event(display_recipient, subject, sender_full_name)

    here = make_where(event)
    assert isinstance(here, Where)
    assert here.stream == display_recipient
    assert here.subject == subject

    # we should also be able to make wheres from contexts.
    here_con = make_where(make_context(event))
    assert here_con == here


# ==================== collectives ====================

@given(text())
def test_coll_init(leader):
    coll = Collective(leader)
    assert leader in coll
    assert len(coll) == 1

@given(text())
def test_coll_immediate_leave(leader):
    coll = Collective(leader)
    coll.remove(leader)
    assert coll.maker is None
    assert not coll.users
    assert not coll.closed

    coll.close()
    assert coll.maker is None
    assert not coll.users
    assert coll.closed


@given(text())
def test_elect_maker(leader):
    coll = Collective(leader)
    assert coll.maker is None
    coll.elect_maker()
    assert coll.maker is leader


@given(text(), text(), text())
def test_random_maker(s1, s2, s3):
    coll = Collective(s1, max_size=3)
    coll.add(s2)
    coll.add(s3)
    coll.elect_maker()
    assert coll.maker in {s1, s2, s3}


# ==================== coffeebot API mocks ====================

def _fake_public_say(content, where):
    # these are assertion checks I want on every public event
    assert isinstance(content, str)
    assert isinstance(where, Where)
    assert isinstance(where.stream, str)
    assert isinstance(where.subject, str)


def _fake_private_say(event):
    # in this case I'm asserting on input, since
    # any private message yields an invariant of "here's the help string"
    # so I really shouldn't care about the contents of the event
    # but we can still assert that fake_private_say was called with
    # the right thing...

    assert isinstance(event, dict)
    assert 'message' in event
    message = event['message']
    assert message['type'] == 'private'
    # this line errs on testing the mocked zulip API
    # assert 'sender_email' in event['message']
    pass


def _fake_emoji_reply(emoji, event):
    assert len(emoji.split()) == 1
    # everything else is a function of the event. won't test it.
    pass


# this isn't called by anything inside coffeebot (this registers on
# Zulip's API and dispatches events) , but is here for completeness

def _fake_listen():
    pass


def _generate_private_message(sender_email, content):
    return {
        "type": "message",
        "message": {
            "type": "private",
            "sender_email": sender_email,
            "content": content,
        }
    }


def _generate_public_message(
        content, sender_full_name='Coffeenot (S2 \'17)',
        sender_email='Coffeenot@fakerealm.com',
        stream='bot-test', subject='arbitrary'):
    return {
        "type": "message",
        "message": {
            "type": "public",
            "display_recipient": stream,
            "subject": subject,
            "sender_full_name": sender_full_name,
            "sender_email": sender_email,
            "content": ("@**Ahmad Jarara (S2 '17)** your testing "
                        "sandbox is posting live data") + content,
        }
    }


def _generate_heartbeat():
    return {
        "type": "heartbeat",
    }


@pytest.fixture
def bot():
    coff = Coffeebot(config=None)
    coff.public_say = _fake_public_say
    coff.private_say = _fake_private_say
    coff.emoji_reply = _fake_emoji_reply
    coff.listen = _fake_listen

    fake_client = namedtuple("Fake_client", ["email"])
    coff.client = fake_client("totally-not-bot@recurse.com")
    return coff


def test_bot_end_to_end(bot):
    bot.dispatch(
        _generate_public_message(
            "@**coffeebot** ping"))
