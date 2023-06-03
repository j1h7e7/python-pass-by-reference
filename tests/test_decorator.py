from src.decorator import pass_by_reference
import pytest


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


@pytest.mark.skip
def test_multi():
    x = 100000
    y = 100000
    add_one(x)
    assert x == 100001


@pytest.mark.skip
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


def test_no_renamed_decorator():
    from src.decorator import pass_by_reference

    @pass_by_reference
    def add_one(x):
        x += 1

    y = 1000000
    add_one(y)
    assert y == 1000001


def test_renamed_decorator():
    from src.decorator import pass_by_reference as new_name

    @new_name
    def add_one(x):
        x += 1

    y = 1000000
    add_one(y)
    assert y == 1000001


def test_multi_name_decorator():
    from src.decorator import pass_by_reference

    new_name = pass_by_reference

    @new_name
    def add_one(x):
        x += 1

    y = 1000000
    add_one(y)
    assert y == 1000001


def test_existing_decorator():
    def my_decorator(f):
        return lambda: 1

    @my_decorator
    @pass_by_reference
    def test_fn():
        return 0

    assert test_fn() == 1
