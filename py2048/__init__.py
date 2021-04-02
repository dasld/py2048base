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

# from __future__ import annotations
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    # Type,
    TYPE_CHECKING,
    Union,
)
from abc import ABC
import sys
from enum import Enum, unique
from pathlib import Path
from collections import namedtuple
from collections.abc import Sequence as AbcSequence
from itertools import count
import pickle

import appdirs  # https://pypi.org/project/appdirs
from more_itertools import unzip


## CONSTANTS
# generic constants
# https://github.com/python/cpython/blob/ebe20d9e7eb138c053958bc0a3058d34c6e1a679/Lib/types.py#L51
ModuleType = type(sys)  # just for annotation purposes
Vector = Sequence[int]
# https://github.com/python/typing/issues/684#issuecomment-548203158
if TYPE_CHECKING:

    class EllipsisType(Enum):
        Ellipsis = "..."

    Ellipsis = EllipsisType.Ellipsis
else:
    EllipsisType = type(Ellipsis)
EMPTY_TUPLE = tuple()  # dummy used in `min` and `max` calls
INFTY = float("inf")
NULL_SLICE = slice(None)
# specific constants
APPNAME = __name__
__version__ = (0, 20)
VERSION = ".".join(map(str, __version__))
DATA_DIR = Path(appdirs.user_data_dir(appname=APPNAME))

TESTING = False


__all__ = [
    # global variables
    "APPNAME",
    "DATA_DIR",
    "INFTY",
    # generic functions
    "typename",
    "hexid",
    "iscontainer",
    "type_check",
    "check_int",
    # exceptions
    "Base2048Error",
    "NegativeIntegerError",
    "ExpectationError",
    # generic classes
    "Point",
    "Line",
    "Directions",
    "paired_with_Directions",  # a function
    "GridIndex",
    # game grid classes
    "BaseGameGrid",
    "SquareGameGrid",
]


## GENERAL-PURPOSE FUNCTIONS
def typename(thing: Any) -> str:
    return type(thing).__name__


def hexid(thing: Any) -> str:
    return hex(id(thing))


def iscontainer(thing: Any) -> bool:
    """Determines whether the argument is iterable, but not a `str`.
    """

    cls = type(thing)
    return issubclass(cls, AbcSequence) and not issubclass(cls, str)


def type_check(
    value: Any, expected: Union[type, Sequence[type]], positive: bool = True
) -> None:
    """If the `positive` argument is True, raises an ExpectationError if the
    type of `value` is not listed in, or differs from, `expected`.
    If `positive` is False, raises the error if the type of `value` is listed
    in, or equals, `expected`.
    """

    if iscontainer(expected):
        match = type(value) in expected
    else:
        match = isinstance(value, expected)
    if match != positive:
        raise ExpectationError(value, expected, positive=positive)


def check_int(i: int) -> None:
    """Raises `ExpectationError` if `obj` is not `int`, and
    `NegativeIntegerError` if it's a negative `int`.
    """

    type_check(i, int)
    if i < 0:
        raise NegativeIntegerError(i)


## CLASSES
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
    """Raised when the type of an argument is incorrect. Just like `TypeError`,
    but more verbose.
    """

    def __init__(
        self,
        problem: Any,
        expectations: Any,
        *args: str,
        positive: bool = True,
    ) -> None:
        if iscontainer(expectations):
            self.expectations = "/".join(map(typename, expectations))
        else:
            self.expectations = typename(expectations)
        self.positive = positive
        self.problem = repr(problem)
        self.problem_type = typename(problem)
        self.message = "" if not args else "".join(map(repr, args)) + ". "
        super().__init__(*args)

    def __str__(self) -> str:
        if self.positive:
            return (
                f"{self.message}Expected {self.expectations}, "
                f"but {self.problem} is {self.problem_type}"
            )
        return (
            f"{self.message}Found {self.problem} of type {self.problem_type}; "
            f"the following class(es) is/are not allowed: {self.expectations}"
        )


# other classes
class Point(namedtuple("Point", "x y")):
    """A namedtuple that stores a pair of non-negatives integers.
    """

    # `__slots__`is "a declaration inside a class that saves memory by
    # pre-declaring space for instance attributes and eliminating instance
    # dictionaries
    # https://docs.python.org/3/glossary.html#__slots__
    __slots__ = ()

    def __init__(self, x: int, y: int) -> None:
        check_int(x)
        check_int(y)

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"

    def __str__(self) -> str:
        return f"<{self.x},{self.y}>"


Line = Tuple[Point]


@unique
class Directions(Enum):
    """The four orthogonal directions in the WASD order. The value of each
    Directions object is it's lowercased name: `Directions.UP.value == "up"`,
    and so on.
    """

    # WASD order
    UP = "up"
    LEFT = "left"
    DOWN = "down"
    RIGHT = "right"

    @classmethod
    def pretty(cls) -> str:
        return ", ".join(map(str, cls))


def paired_with_Directions(keys):
    got, target = len(keys), len(Directions)
    if got != target:
        raise ValueError(f"Must pair with exactly {target} keys; {got} found")
    return dict(zip(keys, Directions))


class GridIndex:
    """This class parses objects passed as indexes to a game grid (any instance
    of any subclass of `BaseGameGrid`.
    We want to allow those grids to be indexed in both directions in one
    statement.
    For example, grid[..., 3] should return the second row, grid[2, 3] should
    return the cell at the first column and the second row, and so on.
    grid[..., ...] copies the grid, just like L[:] copies a `list`.

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
        if not args:
            x = y = NULL_SLICE
        elif len(args) == 1:
            the_arg = args[0]
            if the_arg is None:
                raise TypeError(f"Cannot make a {cls} from None")
            # suppose it's a pair and try to unpack it
            try:
                x, y = the_arg
            except (ValueError, TypeError):
                x, y = the_arg, NULL_SLICE
        elif len(args) == 2:
            if None in args:
                raise TypeError(f"Cannot make a {cls} from None")
            x, y = args
        else:
            raise ValueError(
                f"Cannot create a {cls} with more than 2 arguments"
            )
        if x is Ellipsis:
            x = NULL_SLICE
        if y is Ellipsis:
            y = NULL_SLICE
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


## MAIN CLASS IN THIS MODULE
class BaseGameGrid(ABC):
    """Wrapper over `dict` that maps Points into objects that must have the
    type CELLCLASS. CELLCLASS is `None`, which means that it must be overidden
    when subclassing this class.
    The class can abstract any table with orthogonally aligned square cells,
    such as the chess and checkers boards, sudoku grids, and so on.
    While the cells must be squares, the table itself can be a rectangle.
    The class provides basic functionality such as iterating over its rows and
    columns and can be indexed by a `GridIndex`, as explained in the docstring
    of that class.
    """

    CELLCLASS: Any = None

    def __init__(self, width: int, height: int) -> None:
        cls = self.CELLCLASS
        if cls is None:
            raise NotImplementedError(
                "CELLCLASS must be overriden when subclassing BaseGameGrid"
            )
        check_int(width)
        check_int(height)
        self.map: Dict[Point, cls] = {}
        for x in range(width):
            for y in range(height):
                point = Point(x, y)
                try:
                    self.map[point] = cls(point)
                except TypeError:
                    self.map[point] = cls()

    def keys(self) -> Iterator[Point]:
        # sorted returns a list
        return iter(sorted(self.map.keys()))

    def values(self) -> Iterator[CELLCLASS]:
        return (self.map[k] for k in self.keys())

    def items(self) -> Iterator[Tuple[Point, CELLCLASS]]:
        return ((k, self.map[k]) for k in self.keys())

    # some synonyms
    __iter__ = keys
    points = keys

    def __len__(self) -> int:
        # this also provides __bool__
        return len(self.map)

    def __eq__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.map == other.map
        return NotImplemented

    @property
    def x_axis(self) -> Iterator[int]:
        yielded = set()
        for x in unzip(self.keys())[0]:
            if x not in yielded:
                yield x
                yielded.add(x)

    @property
    def y_axis(self) -> Iterator[int]:
        yielded = set()
        for y in unzip(self.keys())[1]:
            if y not in yielded:
                yield y
                yielded.add(y)

    @property
    def width(self) -> int:
        return len(tuple(self.x_axis))

    @property
    def height(self) -> int:
        return len(tuple(self.y_axis))

    @property
    def columns(self) -> Iterator[Line]:
        return (self[x] for x in self.x_axis)

    @property
    def rows(self) -> Iterator[Line]:
        return (self[..., y] for y in self.y_axis)

    def check_integrity(self) -> None:
        # check columns
        # the following ensures that there are no "gaps" nor "jumps" in the
        # column indexes, and then in the row indexes
        for actual, target in zip(self.x_axis, count()):
            if actual != target:
                raise ValueError(
                    f"Wrong column index {actual}; must be {target}"
                )
        shortest = min(tuple(self.columns), default=EMPTY_TUPLE)
        longest = max(tuple(self.columns), default=EMPTY_TUPLE)
        assert len(shortest) == len(longest)
        # check rows
        for actual, target in zip(self.y_axis, count()):
            if actual != target:
                raise ValueError(f"Wrong row index {actual}; must be {target}")
        shortest = min(tuple(self.rows), default=EMPTY_TUPLE)
        longest = max(tuple(self.rows), default=EMPTY_TUPLE)
        assert len(shortest) == len(longest)
        # type check and total size check
        for value in self.values():
            assert isinstance(value, self.CELLCLASS)
        assert len(self) == self.height * self.width

    def pickle(self, path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def unpickle(
        path, ignore_missing: bool = True
    ) -> Optional["BaseGameGrid"]:
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            if not ignore_missing:
                raise

    @staticmethod
    def slice2range(s: slice) -> range:
        # slice objects have read-only data attributes start, stop and step
        # which merely return the argument values (or their default).
        start = s.start or 0
        stop = s.stop or sys.maxsize
        step = s.step or 1
        return range(start, stop, step)

    def select_keys(self, key: GridIndex.Type) -> Line:
        x, y = GridIndex(key)
        restrictions: Set[Callable] = set()
        # restricting the X-axis
        if isinstance(x, int):
            restrictions.add(lambda key: key.x == x)
        elif isinstance(x, slice) and x != NULL_SLICE:
            x_range = self.slice2range(x)
            restrictions.add(lambda key: key.x in x_range)
        # restricting the Y-axis
        if isinstance(y, int):
            restrictions.add(lambda key: key.y == y)
        elif isinstance(y, slice) and y != NULL_SLICE:
            y_range = self.slice2range(y)
            restrictions.add(lambda key: key.y in y_range)
        # assembling everything
        selected: List[Point] = []
        for this_key in self:
            for restriction in restrictions:
                # a break in a for-loop skips its else-clause
                if not restriction(this_key):
                    # the first restriction that doesn't apply is enough to
                    # discard this key
                    break
            else:  # happens iff the for-clause didn't end with a break
                selected.append(this_key)
        return tuple(selected)

    def __getitem__(self, key: GridIndex.Type) -> Union[Point, Line]:
        if isinstance(key, Point):
            # no need for further complications when getting a single Point
            # we don't use `dict.get` here because another function might want
            # to catch the `KeyError`
            return self.map[key]
        selected = tuple(
            (self.map[selected] for selected in self.select_keys(key))
        )
        if not selected:
            raise KeyError
        if len(selected) == 1:
            return selected[0]
        return selected

    def set_point(self, key: Point, value: Any) -> None:
        """This method exists to be overriden by subclasses, if necessary.
        """

        type_check(value, self.CELLCLASS)
        self.map[key] = value

    def __setitem__(
        self, key: GridIndex.Type, value: Union[int, CELLCLASS]
    ) -> None:
        if isinstance(key, Point):
            # no need for further complications when setting a single Point
            self.set_point(key, value)
            return
        selected = self.select_keys(key)
        amount = len(selected)
        if not iscontainer(value):
            value = [value] * amount
        elif len(value) != amount:
            raise ValueError(
                "Wrong amount of values to unpack: "
                f"expected {amount}, got {len(value)}"
            )
        for point, n in zip(selected, value):
            self.set_point(point, n)
        self.check_integrity()

    def __repr__(self) -> str:
        cls = typename(self)
        cellclass = typename(self.CELLCLASS)
        w, h = self.width, self.height
        return f"{cls}('{cellclass}', {w} x {h})"

    def __str__(self) -> str:
        return "\n".join(map(repr, self.rows))


class SquareGameGrid(BaseGameGrid):
    """Exactly like BaseGameGrid, but enforced to remain a square table.
    """

    def __init__(self, side: int) -> None:
        super().__init__(side, side)

    def check_integrity(self) -> None:
        super().check_integrity()
        if self.width != self.height:
            raise ValueError(
                "A SquareGameGrid cannot have different side lenghts, but "
                f"width is {self.width} and height is {self.height}"
            )


def demonstration() -> None:
    # from random import randint

    class IntGameGrid(BaseGameGrid):
        CELLCLASS = int

    g = IntGameGrid(4, 3)
    print(g)
    print("-" * 79)

    for col in range(g.width):
        g[col, ...] = col
    g[..., 0] = (9, 8, 7, 6)

    print(g)
    print("-" * 79)

    rows, cols = tuple(g.rows), tuple(g.columns)
    print(rows)
    print(cols)
    print(g[1:, 1:])


if __name__ == "__main__":
    demonstration()
