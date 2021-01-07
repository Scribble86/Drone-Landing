import itertools
from numbers import Real
from typing import Sequence

import numpy as np
from shapely.geometry import LineString, Point


def adjacent_pairs(lst: Sequence):
    """Return pairs of items in the list that are adjacent.

    >>> adjacent_pairs([1, 2, 3])
    [(1, 2), (2, 3), (3, 1)]
    >>> adjacent_pairs([15, 22, 13, 6])
    [(15, 22), (22, 13), (13, 6), (6, 15)]
    """
    return list(zip(lst, itertools.chain(lst[1:], lst[:1])))


def calc_center(hull: Sequence[Sequence[float]]) -> Point:
    """Calculate the apparent center of the hull of a projected square.

    >>> calc_center([(-1, 1), (-1, -1), (1, -1), (1, 1)]) == Point(0, 0)
    True

    """
    l1 = LineString([hull[0], hull[2]])
    l2 = LineString([hull[1], hull[3]])
    return l1.intersection(l2)


def cos_between_vectors(v1: Sequence[Real], v2: Sequence[Real]) -> np.ndarray:
    """Computes the cosine of the angle between vectors v1 and v2.

    >>> cos_between_vectors(np.array([1, 0, 0]), np.array([0, 1, 0]))
    0.0

    >>> cos_between_vectors(np.array([1, 0, 0]), np.array([1, 0, 0]))
    1.0

    >>> cos_between_vectors(np.array([1, 0, 0]), np.array([-1, 0, 0]))
    -1.0
    """
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
