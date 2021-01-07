from enum import Enum, unique


@unique
class AngleUnit(Enum):
    """An enumeration of available units to use for angles."""
    DEGREES = 1
    RADIANS = 2
