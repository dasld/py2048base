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

import pickle
import sys
from abc import ABC
from collections import namedtuple
from enum import Enum
from itertools import count, repeat
from pathlib import Path
from typing import (
    Callable,
    Dict,
    Hashable,
    Iterator,
    Literal,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

import appdirs  # https://pypi.org/project/appdirs

# CONSTANTS specific to this package
# declaring them here, before importing utils, because
# utils require them (avoiding circular importing errors)
_TESTING = False  # used only in setup.py
__version__ = (0, 42)
APPNAME = __name__
DATA_DIR = Path(appdirs.user_data_dir(appname=APPNAME))
VERSION = ".".join(map(str, __version__))

from py2048.utils import (
    EMPTY_TUPLE,
    NONE_SLICE,
    Base2048Error,
    EllipsisType,
    Expectation,
    ExpectationError,
    IntPair,
    NegativeIntegerError,
    check_int,
    classname,
    hexid,
    is_container,
    type_check,
    typename,
)


__all__ = [
    # global variables
    "__version__",
    "APPNAME",
    "DATA_DIR",
    "VERSION",
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


# other classes
class Point(namedtuple("_Point", "x y")):
    """Namedtuple containing a pair of non-negative integers.
    """

    # `__slots__`is "a declaration inside a class that saves memory by
    # pre-declaring space for instance attributes and eliminating instance
    # dictionaries"
    # https://docs.python.org/3/glossary.html#__slots__
    __slots__ = ()

    def __new__(cls, x: int, y: int) -> Point:
        # using __new__ instead of __init__ because tuples are immutable
        # https://stackoverflow.com/a/3624799
        check_int(x)
        check_int(y)
        self = super(Point, cls).__new__(cls, x, y)
        return self

    def __add__(self, other: IntPair) -> IntPair:
        """>>> Point(x=3, y=2) + (-1, 0)
               (2, 2)
        """

        try:
            return self.x + other[0], self.y + other[1]
        except (TypeError, ValueError, IndexError, KeyError):
            return NotImplemented

    def __str__(self) -> str:
        return f"<{self.x},{self.y}>"


Line = Tuple[Point, ...]
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
    Type = Union[SingletonType, Tuple[SingletonType, SingletonType]]
    _NONE_MSG = "Cannot make a GridIndex from None"

    def __init__(self, *args: Type) -> None:
        length = len(args)
        if not length:
            x = y = NONE_SLICE
        elif length == 1:
            the_arg = args[0]
            if the_arg is None:
                raise TypeError(self._NONE_MSG)
            # suppose it's a pair and try to unpack it
            try:
                x, y = the_arg
            except (ValueError, TypeError):
                x, y = the_arg, NONE_SLICE
        elif length == 2:
            if None in args:
                raise TypeError(self._NONE_MSG)
            x, y = args
        else:
            cls = typename(self)
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
    `CELLCONSTRUCTOR`, if overridden, must be a function that either takes as
    single argument a `Point`, or no argument, and returns an instance of
    `CELLCLASS`. If not overridden, it defaults to `CELLCLASS.__init__`.
    The class can abstract any table with orthogonally aligned square cells,
    such as chess and checkers boards, sudoku grids, and so on.
    While the cells must be squares, the table itself can be a rectangle.
    The class provides basic functionality such as iterating over its rows and
    columns and can be indexed by a `GridIndex`, as explained in the docstring
    of that class.
    """

    CELLCLASS: Type = None
    CELLCONSTRUCTOR: Optional[Callable] = None

    def __init__(self, width: int, height: int) -> None:
        cellclass = self.CELLCLASS
        if cellclass is None:
            raise NotImplementedError(
                "CELLCLASS must be overridden when subclassing BaseGameGrid"
            )
        check_int(width)
        check_int(height)
        if width < 2 or height < 2:
            raise ValueError(
                "'width' and 'height' must be both greater than or equal to 2"
            )
        self.mapping: Dict[Point, cellclass] = {}
        constructor = self.CELLCONSTRUCTOR or cellclass
        for x in range(width):
            for y in range(height):
                point = Point(x, y)
                try:
                    self.mapping[point] = constructor(point)
                except TypeError:
                    self.mapping[point] = constructor()
        self.check_integrity()

    # -- "private" methods (except `repr` and `str`)
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

    def _axisX(self, reverse: bool = False) -> Iterator[int]:
        """Yield each x number in ascending or descending order.
        """

        return iter(sorted(self._distinct_xs, reverse=reverse))

    def _axisY(self, reverse: bool = False) -> Iterator[int]:
        """Yield each y number in ascending or descending order.
        """

        return iter(sorted(self._distinct_ys, reverse=reverse))

    @staticmethod
    def _slice2range(s: slice) -> range:
        """'Cast' a `slice` into a `range`.

        Needed because ranges allow containment tests, but slices don't.
        3 in range(4) -> True
        3 in slice(4) -> TypeError
        """

        # https://docs.python.org/3.8/library/functions.html#slice
        # `start` and `step` are optional in slice creation, but they default
        # to `None`, which is why we provide integer defaults
        # it's better to explicitly check for `None` instead of checking any
        # falsy value; based on:
        # https://github.com/more-itertools/more-itertools/blob/76f51e4f11c9ff99ed080ca536fbd4735bbfae3f/more_itertools/more.py#L361
        start = 0 if (s.start is None) else s.start
        stop = sys.maxsize if (s.stop is None) else s.stop
        step = 1 if (s.step is None) else s.step
        return range(start, stop, step)

    def _select_keys(self, key: GridIndex.Type) -> Line:
        """Yield each Point that matches `key`.
        """

        x, y = GridIndex(key)
        restrictions: Set[Callable[[Point], bool]] = set()
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
        # yielding only what fits the restrictions
        for point in self:
            for restr in restrictions:
                # a break in a for-loop skips its else-clause
                if not restr(point):
                    # the first restriction that doesn't apply is enough to
                    # discard this key
                    break
            else:
                yield point

    def __getitem__(self, key: GridIndex.Type) -> Union[Point, Line]:
        """Return either one Point or a tuple of Points.
        """

        if isinstance(key, Point):
            # no need for further complications when getting a single Point
            # we don't use `dict.get` here because another function might want
            # to catch the `KeyError`
            return self.mapping[key]
        selecteds = tuple(self.mapping[sel] for sel in self._select_keys(key))
        if not selecteds:
            raise KeyError(str(key))
        if len(selecteds) == 1:
            return selecteds[0]
        return selecteds

    def _set_point(self, key: Point, value: CELLCLASS) -> None:
        """Assign a value to one Point.

        This method exists to be overridden by subclasses, if necessary.
        """

        type_check(value, self.CELLCLASS)
        self.mapping[key] = value

    def _set_xy(self, x: int, y: int, value: CELLCLASS) -> None:
        self._set_point(Point(x, y), value)

    def __setitem__(
        self, key: GridIndex.Type, value: Union[int, CELLCLASS]
    ) -> None:
        if isinstance(key, Point):
            # no need for further complications when setting a single Point
            self._set_point(key, value)
            return
        selecteds = tuple(self._select_keys(key))
        if not selecteds:
            raise KeyError(str(key))
        if not is_container(value):
            value = repeat(value)
        elif len(value) != len(selecteds):
            raise ValueError(
                "Bad amount of values to unpack: "
                f"expected {len(selecteds)}, got {len(value)}"
            )
        for point, point_value in zip(selecteds, value):
            self._set_point(point, point_value)
        self.check_integrity()

    # -- "public" methods
    def keys(self, by: Literal["row", "column"] = "row") -> Iterator[Point]:
        by = by.lower()
        # sorted returns a list
        if by == "row":
            return iter(sorted(self.mapping.keys(), key=lambda point: point.y))
        if by == "column":
            return iter(sorted(self.mapping.keys()))
        raise ValueError(f"'by' must be 'row' or 'column', not {by!r}")

    def values(
        self, by: Literal["row", "column"] = "row"
    ) -> Iterator[CELLCLASS]:
        return (self.mapping[k] for k in self.keys(by=by))

    def items(
        self, by: Literal["row", "column"] = "row"
    ) -> Iterator[Tuple[Point, CELLCLASS]]:
        return ((k, self.mapping[k]) for k in self.keys(by=by))

    # some synonyms
    __iter__ = keys
    points = keys

    @property
    def width(self) -> int:
        return len(self._distinct_xs)

    @property
    def height(self) -> int:
        return len(self._distinct_ys)

    def columns(self, reverse: bool = False) -> Iterator[Line]:
        return (self[x] for x in self._axisX(reverse=reverse))

    def rows(self, reverse: bool = False) -> Iterator[Line]:
        return (self[..., y] for y in self._axisY(reverse=reverse))

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

        self_len = len(self)
        if not self_len:  # you can't have a problem if you have nothing :)
            return
        width, height = self.width, self.height
        # check columns
        for actual, target in zip(self._axisX(), count()):
            assert (
                actual == target
            ), f"Bad column index {actual}; must be {target}"
        short_len = len(min(tuple(self.columns()), default=EMPTY_TUPLE))
        long_len = len(max(tuple(self.columns()), default=EMPTY_TUPLE))
        assert short_len == long_len, (
            f"Shortest column has length {short_len}, "
            f"but the longest has length {long_len}"
        )
        # 4 columns means 0..3, 9 columns means 0..8, etc.
        max_distinct_xs = max(self._distinct_xs)
        assert max_distinct_xs == (width - 1), (
            f"Width of {self!r} is {width}, but "
            f"there are {max_distinct_xs} X values"
        )
        # check rows
        for actual, target in zip(self._axisY(), count()):
            assert actual == target, f"Bad row index {actual}; must be {target}"
        short_len = len(min(tuple(self.rows()), default=EMPTY_TUPLE))
        long_len = len(max(tuple(self.rows()), default=EMPTY_TUPLE))
        assert short_len == long_len, (
            f"Shortest row has length {short_len}, "
            f"but the longest has length {long_len}"
        )
        max_distinct_ys = max(self._distinct_ys)
        assert max_distinct_ys == (height - 1), (
            f"Height of {self!r} is {height}, but "
            f"there are {max_distinct_ys} Y values"
        )
        # type check
        for value in self.values():
            type_check(value, self.CELLCLASS)
        # total size check
        width_height = width * height
        assert self_len == width_height, (
            f"{self!r} has {self_len} items, but "
            f"self.height * self.width == {width_height}"
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

    # -- `repr` and `str`
    def __repr__(self) -> str:
        my_name, cellclass = typename(self), typename(self.CELLCLASS)
        return f"{my_name}({cellclass=}, {self.width=}, {self.height=})"

    def __str__(self) -> str:
        return "\n".join(repr(r).strip(")(") for r in self.rows())


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
