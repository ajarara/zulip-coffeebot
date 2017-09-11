from coffeebotv2 import parse
from coffeebotv2 import Where, Context, Collective, Coffeebot

from hypothesis import given
from hypothesis.strategies import from_regex, text


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



# ==================== collectives ====================

def test_coll_init():
    coll = Collective("frog")
    assert "frog" in coll
    assert len(coll) == 1


def test_coll_immediate_leave():
    coll = Collective("frog")
    coll.remove("frog")
    assert coll.maker is None
    assert not coll.users
    assert not coll.closed

    coll.close()
    assert coll.maker is None
    assert not coll.users
    assert coll.closed
