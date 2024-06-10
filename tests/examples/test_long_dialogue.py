import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(__file__, '../../..')))  # noqa

ROOT_RESOURCE = os.path.abspath(os.path.join(__file__, '../../../examples/resource'))  # noqa
from examples.long_dialogue import test as long_dialogue  # noqa


def test_long_dialogue():
    long_dialogue()
