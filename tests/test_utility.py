import numpy as np
from wrftamer.utility import printProgressBar, get_random_string
import pytest


def test_printPogressBar():
    rawlist = np.arange(1000)
    total = len(rawlist)
    printProgressBar(0, total, prefix="Progress:", suffix="Complete", length=50)
    for i, rawfile in enumerate(rawlist):
        printProgressBar(i + 1, total, prefix="Progress:", suffix="Complete", length=50)


def test_printPogressBar2():
    rawlist = np.arange(0)
    total = len(rawlist)
    printProgressBar(0, total, prefix="Progress:", suffix="Complete", length=50)


def test_get_random_string1():
    with pytest.raises(ValueError):
        res = get_random_string(-100)

    with pytest.raises(ValueError):
        res = get_random_string(0)


def test_get_random_string2():
    res = get_random_string(100)

    if isinstance(res, str):
        pass
