from src.decorator import pass_by_reference


@pass_by_reference
def add_one(x):
    x += 1


def test_basic():
    x = 100000
    add_one(x)
    assert x == 100001


def test_singleton():
    x = 1
    add_one(x)
    assert x == 2


def test_multi():
    x = 100000
    y = 100000
    add_one(x)
    assert x == 100001


def test_same_id():
    x = 1
    y = 1
    add_one(x)
    assert x == 2
    assert y == 1


def test_global():
    global x
    x = 1
    add_one(x)
    assert x == 2


def test_nonlocal():
    x = 1

    def thing():
        nonlocal x
        add_one(x)
        assert x == 2

    thing()
    assert x == 2
