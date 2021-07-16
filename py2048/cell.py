# -*- coding: utf-8 -*-
#
# cell.py
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

"""Declares the `Cell` class, which represents one tile
in the game grid.
"""

from functools import partialmethod
from typing import Sequence

from py2048.core import Point
from py2048.utils import (
    ExpectationError,
    InvalidCellIntError,
    either_0_power2,
    type_check,
)


class Cell:
    """Individual number in the 2048 grid.

    The `Point` of each a `Cell` 'c' can be accessed as `c.point`,
    and its coordinates can be directly accessed as `c.x` and `c.y`.
    Besides storing and validating integers, it contains a `_lock`
    boolean that represents whether it can move in this cycle
    (this prevents an 8 moving into another 8 and the resulting 16
    merging into another 16, for example.
    """

    def __init__(self, point: Point, number: int = 0) -> None:
        type_check(point, Point)
        self.point = point
        self.x, self.y = point
        self._lock = False
        # don't use self._number here; we want bad initial values to be
        # detected
        self.number: int = number

    @property
    def number(self) -> int:
        return self._number

    @number.setter
    def number(self, value: int) -> None:
        if not isinstance(value, int):
            raise ExpectationError(value, int)
        if not either_0_power2(value):
            raise InvalidCellIntError(
                f"Cannot assign non-power of 2 {value} to {self!r}"
            )
        self._number = value

    def __bool__(self) -> bool:
        return bool(self._number)

    def __eq__(self, other) -> bool:
        # docs state that 'If a class does not define an `__eq__()`
        # method it should not define a `__hash__()` operation either'.
        # We want to define `__hash__`, so we must define `__eq__` as
        # well. Two Cells are the same iff they're at the same place,
        # no matter their number.
        if isinstance(other, type(self)):
            return self.point == other.point
        return NotImplemented

    def __hash__(self) -> int:
        # we want Cells to be hashable so that they can be used in sets
        # if two objects test as equal, then they MUST have the same
        # hash value objects that have a hash MUST produce the same
        # hash over time
        return hash((type(self), self.x, self.y))

    def __gt__(self, other) -> bool:
        # defined just to allow Cells to be ordered and sorted
        if isinstance(other, type(self)):
            return self.point > other.point
        return NotImplemented

    def _set_lock(self, onoff: bool) -> None:
        type_check(onoff, bool)
        self._lock = onoff

    is_locked = property(
        fget=lambda self: self._lock,
        fset=_set_lock,
        doc=(
            "`_lock` is a `bool` that tells whether the `Cell` has already "
            "moved this cycle. This prevents a 2 merging into a 2 and the "
            "resulting 4 merging into another 4 all in a single movement, "
            "for example."
        ),
    )

    lock = partialmethod(_set_lock, True)
    unlock = partialmethod(_set_lock, False)

    def __repr__(self) -> str:
        return f"Cell({self.x}, {self.y}, {self._number})"

    def __str__(self) -> str:
        return str(self._number)


Tissue = Sequence[Cell]
