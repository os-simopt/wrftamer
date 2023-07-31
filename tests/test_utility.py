from src.wrftamer import get_random_string
import pytest

# works

def test_get_random_string1():
    with pytest.raises(ValueError):
        res = get_random_string(-100)

    with pytest.raises(ValueError):
        res = get_random_string(0)


def test_get_random_string2():
    res = get_random_string(100)

    if isinstance(res, str):
        pass
