# -*- coding: utf-8 -*-
#
# __init__.py
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

# allowing postponed evaluation of annotations; see:
# https://www.python.org/dev/peps/pep-0563/
from __future__ import annotations

import inspect
import pickle
import sys
from abc import ABC
from collections import namedtuple
from collections.abc import Collection
from enum import Enum
from itertools import count
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Hashable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

import appdirs  # https://pypi.org/project/appdirs

from py2048.constants import EMPTY_TUPLE, NONE_SLICE, EllipsisType, Expectation

# CONSTANTS specific to this package
# _TESTING is used only in setup.py
_TESTING = False

__version__ = (0, 37)
APPNAME = __name__
DATA_DIR = Path(appdirs.user_data_dir(appname=APPNAME))
VERSION = ".".join(map(str, __version__))

__all__ = [
    # global variables
    "__version__",
    "APPNAME",
    "DATA_DIR",
    "VERSION",
    # generic functions
    "check_int",
    "classname",
    "hexid",
    "iscontainer",
    "type_check",
    "typename",
    # exceptions
    "Base2048Error",
    "ExpectationError",
    "NegativeIntegerError",
    # generic classes
    "Directions",
    "GridIndex",
    "Line",
    "Point",
    "Snapshot",
    # game grid classes
    "BaseGameGrid",
    "SquareGameGrid",
]


# GENERAL-PURPOSE FUNCTIONS
def typename(thing: Any) -> str:
    """Return the name of its argument's class.
    """

    return type(thing).__name__


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


def iscontainer(thing: Any) -> bool:
    """Determine whether the argument is an iterable, but not a `str`.
    """

    cls = type(thing)
    return issubclass(cls, Collection) and not issubclass(cls, str)


def type_check(
    value: Any, expected: Expectation, positive: bool = True
) -> None:
    """Verify whether `value` is of an appropriate type, or is not of a
    forbidden one.

    :param Any value: the object to check
    :param Expectation expected: a class or a sequence of classes
    :param bool positive: if `True`, raises `ExpectationError` if the type of
        `value` is not listed in, or differs from, `expected`.
        If `False`, raises the error if the type of `value` is listed in, or
         equals, `expected`.
    """

    if iscontainer(expected):
        match = type(value) in expected
    else:
        match = isinstance(value, expected)
    if match != positive:
        raise ExpectationError(value, expected, positive=positive)


def check_int(i: int) -> None:
    """Raise `ExpectationError` if `obj` is not `int`, and
    `NegativeIntegerError` if it's a negative `int`.
    """

    type_check(i, int)
    if i < 0:
        raise NegativeIntegerError(i)


# CLASSES
# Exceptions
class Base2048Error(Exception):
    pass


class NegativeIntegerError(Base2048Error, ValueError):
    """Raised when a negative `int` is found when a positive one or 0 was
    required.
    """

    std_message = f"Only non-negative integers can be used in a {APPNAME} grid"

    def __init__(self, number: int, message: str = "") -> None:
        self.number = number
        self.message = f"{message}. " if message else ""
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.message}{self.std_message}; but {self.number} found"


class ExpectationError(Base2048Error, TypeError):
    """Raised when the type of an argument is incorrect.

    Just like `TypeError`, but more verbose.
    """

    def __init__(
        self,
        problem: Any,
        expectation: Expectation,
        *args: str,
        positive: bool = True,
    ) -> None:
        if iscontainer(expectation):
            self.expectation = "/".join(map(classname, expectation))
        else:
            self.expectation = classname(expectation)
        self.positive = positive
        self.problem = repr(problem)
        self.problem_type = typename(problem)
        if args:
            self.message = "".join(args).rstrip() + ". "
        else:
            self.message = ""
        super().__init__(*args)

    def __str__(self) -> str:
        if self.positive:
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


# other classes
class Point(namedtuple("Point", "x y")):
    """Namedtuple that stores a pair of non-negative integers.
    """

    # `__slots__`is "a declaration inside a class that saves memory by
    # pre-declaring space for instance attributes and eliminating instance
    # dictionaries"
    # https://docs.python.org/3/glossary.html#__slots__
    __slots__ = ()

    def __new__(cls, x: int, y: int) -> None:
        # using __new__ instead of __init__ because tuples are immutable
        # https://stackoverflow.com/a/3624799
        check_int(x)
        check_int(y)
        self = super(Point, cls).__new__(cls, x, y)
        return self

    def __str__(self) -> str:
        return f"<{self.x},{self.y}>"


Line = Tuple[Point]
Snapshot = Mapping[Point, int]


class Directions(Enum):
    """The four orthogonal directions in the WASD order.

    The value of each `Directions` object is its lowercase name:
    `Directions.UP.value == "up"`, and so on.
    """

    # WASD order
    UP = "up"
    LEFT = "left"
    DOWN = "down"
    RIGHT = "right"

    @classmethod
    def pretty(cls) -> str:
        return ", ".join(map(str, cls))

    @classmethod
    def paired_with(cls, keys) -> Dict[Hashable, Directions]:
        got, target = len(keys), len(cls)
        if got != target:
            raise ValueError(
                f"Must pair with exactly {target} keys; {got} found"
            )
        return dict(zip(keys, cls))


class GridIndex:
    """One or two values that index a game grid.

    This class parses objects passed as indexes to a game grid (any instance
    of any subclass of `BaseGameGrid`): we want to allow those grids to be
    indexed in both directions in one statement.

    For example, grid[..., 3] should return the third row, grid[2, 3] should
    return the cell at the second column and the third row, and so on.
    grid[..., ...] copies the grid, just like L[:] copies a `list` L.

    The class expects either a single argument, or a tuple with exactly two
    arguments.
    Each argument must be either an `Ellipsis` literal, an `int`, or a `slice`.
    Integers cannot be negative.
    `Ellipsis` is converted into the "null slice", which is `slice(None)`. It
    represents that all rows, or all columns, are being selected.
    If only one object is passed, it is assigned to the x-axis, and the y-index
    defaults to the null slice.
    """

    SingletonType = Union[int, slice, EllipsisType]
    Type = Union[SingletonType, Tuple[SingletonType]]

    def __init__(self, *args: Sequence[SingletonType]) -> None:
        cls = typename(self)
        none_error = f"Cannot make a {cls} from None"
        length = len(args)
        if not length:
            x = y = NONE_SLICE
        elif length == 1:
            the_arg = args[0]
            if the_arg is None:
                raise TypeError(none_error)
            # suppose it's a pair and try to unpack it
            try:
                x, y = the_arg
            except (ValueError, TypeError):
                x, y = the_arg, NONE_SLICE
        elif length == 2:
            if None in args:
                raise TypeError(none_error)
            x, y = args
        else:
            raise ValueError(
                f"Cannot create a {cls} with more than 2 arguments"
            )
        if x is Ellipsis:
            x = NONE_SLICE
        if y is Ellipsis:
            y = NONE_SLICE
        pair = (x, y)
        for i in pair:
            if not isinstance(i, slice):
                check_int(i)
        self.x = x
        self.y = y
        self.xy = pair
        self._str = str(pair)

    def __iter__(self) -> Iterator[SingletonType]:
        return iter(self.xy)

    def __getitem__(self, key: int) -> SingletonType:
        return self.xy[key]

    def __eq__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.xy == other.xy
        return NotImplemented

    def __hash__(self) -> int:
        return hash((type(self), self.x, self.y))

    def __repr__(self) -> str:
        return typename(self) + self._str

    def __str__(self) -> str:
        return self._str


# MAIN CLASS IN THIS MODULE
class BaseGameGrid(ABC):
    """Mapping of `Points` into `CELLCLASS` instances.

    `CELLCLASS` is `None`, which means that it must be overridden
    when subclassing this class.
    The class can abstract any table with orthogonally aligned square cells,
    such as the chess and checkers boards, sudoku grids, and so on.
    While the cells must be squares, the table itself can be a rectangle.
    The class provides basic functionality such as iterating over its rows and
    columns and can be indexed by a `GridIndex`, as explained in the docstring
    of that class.
    """

    CELLCLASS: Type = None

    def __init__(self, width: int, height: int) -> None:
        cls = self.CELLCLASS
        if cls is None:
            raise NotImplementedError(
                "CELLCLASS must be overridden when subclassing BaseGameGrid"
            )
        check_int(width)
        check_int(height)
        if width < 2 or height < 2:
            raise ValueError(
                "'width' and 'height' must be both greater than or equal to 2"
            )
        self.mapping: Dict[Point, cls] = {}
        for x in range(width):
            for y in range(height):
                point = Point(x, y)
                try:
                    self.mapping[point] = cls(point)
                except TypeError:
                    self.mapping[point] = cls()

    def keys(self) -> Iterator[Point]:
        # sorted returns a list
        return iter(sorted(self.mapping.keys()))

    def values(self) -> Iterator[CELLCLASS]:
        return (self.mapping[k] for k in self.keys())

    def items(self) -> Iterator[Tuple[Point, CELLCLASS]]:
        return ((k, self.mapping[k]) for k in self.keys())

    # some synonyms
    __iter__ = keys
    points = keys

    def __len__(self) -> int:
        # this also provides __bool__
        return len(self.mapping)

    def __eq__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.mapping == other.mapping
        return NotImplemented

    @property
    def _distinct_xs(self) -> Set[int]:
        return set(point.x for point in self.mapping.keys())

    @property
    def _distinct_ys(self) -> Set[int]:
        return set(point.y for point in self.mapping.keys())

    def x_axis(self, reverse: bool = False) -> Iterator[int]:
        """Yield each x number in ascending or descending order.
        """

        return iter(sorted(self._distinct_xs, reverse=reverse))

    def y_axis(self, reverse: bool = False) -> Iterator[int]:
        """Yield each y number in ascending or descending order.
        """

        return iter(sorted(self._distinct_ys, reverse=reverse))

    @property
    def width(self) -> int:
        return len(self._distinct_xs)

    @property
    def height(self) -> int:
        return len(self._distinct_ys)

    def columns(self, reverse: bool = False) -> Iterator[Line]:
        return (self[x] for x in self.x_axis(reverse=reverse))

    def rows(self, reverse: bool = False) -> Iterator[Line]:
        return (self[..., y] for y in self.y_axis(reverse=reverse))

    def check_integrity(self) -> None:
        """Ensure the grid's dimensions and indexes are correct.


        First, this checks that there are neither "gaps" nor "jumps" in
        the column indexes and that the shortest and longest columns are the
        same length.
        Then, it does the same with the rows.
        It checks that each value in `self.values()` is still an instance of
        `self.CELLCLASS`.
        It ensures the amount of pairs in the mapping equals
        `self.width * self.height`.
        """

        # check columns
        for actual, target in zip(self.x_axis(), count()):
            assert (
                actual == target
            ), f"Bad column index {actual}; must be {target}"
        short_len = len(min(tuple(self.columns()), default=EMPTY_TUPLE))
        long_len = len(max(tuple(self.columns()), default=EMPTY_TUPLE))
        assert short_len == long_len, (
            f"Shortest column has length {short_len}, "
            f"but the longest has length {long_len}"
        )
        # check rows
        for actual, target in zip(self.y_axis(), count()):
            assert actual == target, f"Bad row index {actual}; must be {target}"
        short_len = len(min(tuple(self.rows()), default=EMPTY_TUPLE))
        long_len = len(max(tuple(self.rows()), default=EMPTY_TUPLE))
        assert short_len == long_len, (
            f"Shortest row has length {short_len}, "
            f"but the longest has length {long_len}"
        )
        # type check
        for value in self.values():
            type_check(value, self.CELLCLASS)
        # total size check
        self_len = len(self)
        height_width = self.height * self.width
        assert self_len == height_width, (
            f"{self!r} has {self_len} items, but "
            f"self.height * self.width == {height_width}"
        )

    def pickle(self, path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def unpickle(path, ignore_missing: bool = True) -> Optional[BaseGameGrid]:
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            if not ignore_missing:
                raise

    @staticmethod
    def _slice2range(s: slice) -> range:
        # https://docs.python.org/3.8/library/functions.html#slice
        # slice objects have read-only data attributes start, stop and step
        # which merely return the argument values (or their default)
        start = s.start or 0
        stop = s.stop or sys.maxsize
        step = s.step or 1
        return range(start, stop, step)

    def select_keys(self, key: GridIndex.Type) -> Line:
        """Return a tuple with all points that match `key`.
        """

        x, y = GridIndex(key)
        restrictions: Set[Callable] = set()
        # restricting the X-axis
        if isinstance(x, int):
            restrictions.add(lambda testing: testing.x == x)
        elif isinstance(x, slice) and x != NONE_SLICE:
            x_range = self._slice2range(x)
            restrictions.add(lambda testing: testing.x in x_range)
        # restricting the Y-axis
        if isinstance(y, int):
            restrictions.add(lambda testing: testing.y == y)
        elif isinstance(y, slice) and y != NONE_SLICE:
            y_range = self._slice2range(y)
            restrictions.add(lambda testing: testing.y in y_range)
        # assembling everything
        selecteds: List[Point] = []
        for point in self:
            for rest in restrictions:
                # a break in a for-loop skips its else-clause
                if not rest(point):
                    # the first restriction that doesn't apply is enough to
                    # discard this key
                    break
            else:  # happens iff the for-clause didn't end with a break
                selecteds.append(point)
        return tuple(selecteds)

    def __getitem__(self, key: GridIndex.Type) -> Union[Point, Line]:
        """Return either one Point or a tuple of Points.
        """

        if isinstance(key, Point):
            # no need for further complications when getting a single Point
            # we don't use `dict.get` here because another function might want
            # to catch the `KeyError`
            return self.mapping[key]
        selecteds = tuple(self.mapping[sel] for sel in self.select_keys(key))
        if not selecteds:
            raise KeyError(str(key))
        if len(selecteds) == 1:
            return selecteds[0]
        return selecteds

    def set_point(self, key: Point, value: CELLCLASS) -> None:
        """Assign a value to one Point.

        This method exists to be overridden by subclasses, if necessary.
        """

        type_check(value, self.CELLCLASS)
        self.mapping[key] = value

    def set_xy(self, x: int, y: int, value: CELLCLASS) -> None:
        self.set_point(Point(x, y), value)

    def __setitem__(
        self, key: GridIndex.Type, value: Union[int, CELLCLASS]
    ) -> None:
        if isinstance(key, Point):
            # no need for further complications when setting a single Point
            self.set_point(key, value)
            return
        selecteds = self.select_keys(key)
        if not selecteds:
            raise KeyError(str(key))
        points_amount = len(selecteds)
        if not iscontainer(value):
            value = [value] * points_amount
        elif len(value) != points_amount:
            raise ValueError(
                "Bad amount of values to unpack: "
                f"expected {points_amount}, got {len(value)}"
            )
        for point, point_value in zip(selecteds, value):
            self.set_point(point, point_value)
        self.check_integrity()

    def __repr__(self) -> str:
        my_name, cell_name = classname(self), classname(self.CELLCLASS)
        w, h = self.width, self.height
        return f"{my_name}('{cell_name}', {w}x{h})"

    def __str__(self) -> str:
        return "\n".join(repr(r) for r in self.rows())


class SquareGameGrid(BaseGameGrid):
    """BaseGameGrid enforced to remain square.
    """

    def __init__(self, side: int) -> None:
        super().__init__(side, side)

    def check_integrity(self) -> None:
        super().check_integrity()
        assert self.width == self.height, (
            "A SquareGameGrid cannot have different side lengths, but "
            f"width=={self.width} and height=={self.height}"
        )
