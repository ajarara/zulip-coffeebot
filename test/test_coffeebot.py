from coffeebot import Collective, Directive, Coffeebot
from coffeebot import CoffeeError, _parse
import pytest

# it doesn't make sense to create a collective without a topic/stream
# tied to it as it has to merge its own internal state with zulip's
# state.
STREAM_SENTINEL = None
TOPIC_SENTINEL = None


def py_test():
    assert True


def test_coll_open():
    col = Collective("user1", TOPIC_SENTINEL, STREAM_SENTINEL)
    assert col.leader == "user1"
    assert len(col) == 1


def test_coll_close():
    col = Collective("user1", TOPIC_SENTINEL, STREAM_SENTINEL)
    col.close()
    assert col.closed
    with pytest.raises(CoffeeError):
        # it bothers me a little bit that you have to take my word for it
        col.add("arbitrary")


def test_coll_remove():
    col = Collective("user1", TOPIC_SENTINEL, STREAM_SENTINEL)
    col.add("doggy!")
    col.remove("doggy!")
    assert len(col) == 1
    assert col.leader


def test_coll_leader_remove():
    col = Collective("user1", TOPIC_SENTINEL, STREAM_SENTINEL)
    col.remove("user1")
    assert len(col) == 0
    assert col.leader is None


def test_coll_add():
    col = Collective("user5", TOPIC_SENTINEL, STREAM_SENTINEL)
    for i in range(4):
        col.add("user{}".format(i))

    assert col.closed
    with pytest.raises(CoffeeError):
        col.add("user6")


def test_coll_dispatch():
    req = Directive("add", "user1")
    col = Collective("user1", TOPIC_SENTINEL, STREAM_SENTINEL)
    col.dispatch(req)
    assert len(col) == 1

    rem_req = Directive("remove", "user1")
    col.dispatch(rem_req)
    assert len(col) == 0

    # hmm maybe this interface is awkward.
    close_req = Directive("close", None)
    col.dispatch(close_req)

    assert col.closed


def test_parse():
    assert _parse("@coffeebot init") == 'init'
    assert _parse("@coffeebot yes") == 'add'
    assert _parse("@coffeebot no") == 'remove'
    # whatever is encountered in command_regs first.
    assert _parse("@coffeebot yes @coffeebot no") == 'add'
    assert _parse("i love you @coffeebot") == 'love'


def _quotifier(words):
    quotes = ("`", "'", '"')
    fmts = ("{}{}{}".format(quote, "{}", quote) for quote in quotes)
    return (fmt.format(words) for fmt in fmts)


def test_quoted_parse():
    phrases = ("@coffeebot no",
               "@coffeebot yes",
               "@coffeebot in",
               "@coffeebot out",
               "@coffeebot init",)

    for phrase in phrases:
        for quoted_phrase in _quotifier(phrase):
            assert _parse(quoted_phrase) is None



def test_coffeebot_init():
    Coffeebot("#coffee")  # noqa


