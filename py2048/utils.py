# -*- coding: utf-8 -*-
#
# utils.py
#
# This file is part of py2048.
#
# py2048 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# py2048 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with py2048.  If not, see <https://www.gnu.org/licenses/>.

"""Declares a few "constants" and auxiliary functions and exceptions.

The "constants" aren't that important to the rest of the package.
Most are just for type-hinting and type annotations.

The functions aren't related to board games at all.
"""

import enum
import inspect
from collections.abc import Collection
from typing import TYPE_CHECKING, Any, Optional, Sequence, Tuple, Type, Union

from py2048 import APPNAME


__all__ = [
    "EMPTY_TUPLE",
    "NONE_SLICE",
    "EllipsisType",
    "Expectation",
    "IntPair",
    "ModuleType",
    "Vector",
    # generic functions
    "check_int",
    "classname",
    "either_0_power2",
    "hexid",
    "is_container",
    "type_check",
    "typename",
    # exceptions
    "Base2048Error",
    "ExpectationError",
    "InvalidCellIntError",
    "NegativeIntegerError",
]


# -- CONSTANTS
# https://github.com/python/cpython/blob/ebe20d9e7eb138c053958bc0a3058d34c6e1a679/Lib/types.py#L51
Expectation = Union[Type, Sequence[Type]]
IntPair = Tuple[int, int]
ModuleType = type(enum)  # just for annotation purposes
Vector = Sequence[int]


# annotating Ellipsis seems to be way more painful than it should >:(
# the only solution I could find is what Guido posted here:
# https://github.com/python/typing/issues/684#issuecomment-548203158
if TYPE_CHECKING:

    class EllipsisType(enum.Enum):
        Ellipsis = "..."

    Ellipsis = EllipsisType.Ellipsis
else:
    EllipsisType = type(Ellipsis)

# I use these "constants" because I find them a bit more readable than
# writing `slice(None)` or `()` everytime
# this is used in __init__.BaseGameGrid.check_integrity
EMPTY_TUPLE = tuple()
# this is used in __init__.GridIndex
NONE_SLICE = slice(None)


# -- GENERAL-PURPOSE FUNCTIONS
def typename(thing: Any) -> str:
    """Return the name of its argument's class.
    """

    return thing.__class__.__name__


def classname(thing: Any) -> str:
    """Return its argument's name, if it's a class,
    or the name of its argument's class.
    """

    if inspect.isclass(thing):
        return thing.__name__
    return typename(thing)


def hexid(thing: Any) -> str:
    """Return the hexadecimal `id` of its argument as a string.
    """

    return hex(id(thing))


def is_container(thing: Any) -> bool:
    """Determine whether the argument is an iterable, but not a `str`.
    """

    cls = type(thing)
    return issubclass(cls, Collection) and not issubclass(cls, str)


def type_check(
    value: Any, expected: Expectation, was_positive: bool = True
) -> None:
    """Verify whether `value` is of an appropriate type, or
    is not of a forbidden one.

    :param Any value: the object to check
    :param Expectation expected: a class or a sequence of classes
    :param bool was_positive: if `True`, raises `ExpectationError` if
           the type of `value` IS NOT listed in, or DIFFERS from,
           `expected`.
           If `False`, raises the error if the type of `value` IS
           listed in, or EQUALS, `expected`.
    """

    if is_container(expected):
        matches = type(value) in expected
    else:
        matches = isinstance(value, expected)
    if matches != was_positive:
        raise ExpectationError(value, expected, was_positive=was_positive)


def check_int(i: int) -> None:
    """Raise `ExpectationError` if `obj` is not `int`, and
    `NegativeIntegerError` if it's a negative `int`.
    """

    type_check(i, int)
    if i < 0:
        raise NegativeIntegerError(i)


def either_0_power2(integer: int) -> bool:
    """Adapted from: https://www.geeksforgeeks.org/python-program-to-find-whether-a-no-is-power-of-two/

    A power of 2 bitwise-AND its predecessor always equals 0.
    :param integer: any `int`
    :return: whether `integer` is either 0 or a (positive) power of 2
    """

    return not integer & (integer - 1)


# -- CLASSES
# Exceptions
class Base2048Error(Exception):
    pass


class NegativeIntegerError(Base2048Error, ValueError):
    """Raised when a negative `int` is found when a positive one or 0
    was required.
    """

    STD_MESSAGE = f"Only non-negative integers can be used in a {APPNAME} grid"

    def __init__(self, number: int, message: Optional[str] = None) -> None:
        self.number = number
        if message:
            self.message = f"{message}. "
            super().__init__(message)
        else:
            self.message = ""
            super().__init__()

    def __str__(self) -> str:
        return f"{self.message}{self.STD_MESSAGE}; but {self.number} found"


class InvalidCellIntError(Base2048Error, ValueError):
    """Raised when a Cell is assigned an invalid value
    (not `int`, negative `int`, non-power of 2 `int`).
    """


class ExpectationError(Base2048Error, TypeError):
    """Raised when the type of an argument is incorrect.

    Just like `TypeError`, but more verbose.
    """

    def __init__(
        self,
        problem: Any,
        expectation: Expectation,
        *args: str,
        was_positive: bool = True,
    ) -> None:
        if is_container(expectation):
            self.expectation = "/".join(map(classname, expectation))
        else:
            self.expectation = classname(expectation)
        self.problem = repr(problem)
        self.problem_type = typename(problem)
        if args:
            self.message = "".join(args).rstrip() + ". "
        else:
            self.message = ""
        self.was_positive = was_positive
        super().__init__(*args)

    def __str__(self) -> str:
        if self.was_positive:
            msg = (
                f"{self.message}Expected {self.expectation}, "
                f"but {self.problem} is {self.problem_type}"
            )
        else:
            msg = (
                f"{self.message}Found {self.problem} of "
                f"type {self.problem_type}, but "
                "the following class(es) is/are "
                f"not allowed: {self.expectation}"
            )
        return msg
