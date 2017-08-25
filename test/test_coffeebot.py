from zulip_coffee import Collective
import pytest


def py_test():
    assert True

def test_coll_open():
    col = Collective("user1")
    assert col.leader == "user1"
    assert len(col) == 1

def test_coll_close():
    col = Collective("user1")
    col.close()
    assert col.closed()
    with pytest.raises(ValueError):
        # it bothers me a little bit that you have to take my word for it
        col.add("arbitrary")
    
