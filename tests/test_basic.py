import pytest
from precision_drone_landing.util import adjacent_pairs

def test_adjacent_pairs():
    assert adjacent_pairs([1,2,3]) == [(1, 2), (2, 3), (3, 1)], "adjacent pairs test failed"