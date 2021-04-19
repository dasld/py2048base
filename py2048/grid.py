# -*- coding: utf-8 -*-
#
# grid.py
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

from typing import (
    List,
    Mapping,
    Optional,
    Set,
    Type,
)
import sys
import logging
from itertools import chain
import random

from py2048 import (
    SquareGameGrid,
    Directions,
    ExpectationError,
    NegativeIntegerError,
    Point,
)
from py2048.cell import Cell


logger = logging.getLogger(__name__)


Snapshot = Mapping[Point, int]


class Grid(SquareGameGrid):
    CELLCLASS: Type = Cell
    # how many cells start non-zero
    STARTING_AMOUNT = 2
    # what values can be seeded in each cell
    SEEDING_VALUES = (2, 4)
    # 2^11 == 2048
    NUMBERS: List[int] = [2 ** power for power in range(1, 12)]
    # sys.maxsize == (2^63) - 1 on 64bits machines
    CEILING = sys.maxsize
    DIRECTIONS = tuple(Directions)

    cells = SquareGameGrid.values

    @classmethod
    def is2048like(cls, n: int) -> bool:
        while cls.NUMBERS[-1] < cls.CEILING and n > cls.NUMBERS[-1]:
            cls.NUMBERS.append(cls.NUMBERS[-1] * 2)
        return n in cls.NUMBERS

    def __init__(self, side: int = 4) -> None:
        logger.info("Creating a %dx%d Grid instance", side, side)
        assert 0 < self.STARTING_AMOUNT < side ** 2
        super().__init__(side)
        self.empty_cells: Set[Cell] = set(self.cells())
        self.history: List[Snapshot] = []
        self.reset(on_init=True)

    def snapshot(self) -> Snapshot:
        return {point: cell.number for point, cell in self.items()}

    def store_snapshot(self):
        self.history.append(self.snapshot())

    def update_with_snapshot(self, snapshot: Snapshot) -> None:
        for point, number in snapshot.items():
            cell = self[point]
            cell.unlock()
            self.set_cell(cell, number)
        self.check_integrity()

    @classmethod
    def new_from_snapshot(cls, snapshot: Snapshot) -> "Grid":
        sqrt = len(snapshot) ** 0.5  # a float
        side = int(sqrt)
        if side != sqrt:
            raise ValueError
        new = cls(side)
        new.update_with_snapshot(snapshot)
        return new

    def undo(self, ignore_empty: bool = True):
        try:
            # the last snapshot is the current state, so we forget it
            del self.history[-1]
            # now the last snapshot is the previous state, so we retrieve and
            # forget it
            snap = self.history.pop()
        except IndexError:
            if not ignore_empty:
                raise
        else:
            self.update_with_snapshot(snap)
            self.store_snapshot()

    def reset(self, on_init: bool = False) -> None:
        self.attempt = 0
        self.cycle = 0
        self.score = 0
        if not on_init:
            for cell in self.cells():
                cell.unlock()
                self.set_cell(cell, 0)
            self.history.clear()
        self.check_integrity()

    @property
    def largest(self) -> int:
        return max((cell.number for cell in self.cells()), default=0)

    @property
    def is_empty(self) -> bool:
        """Returns whether every Cell is empty (ie, 0-numbered).
        """
        assert len(self.empty_cells) <= len(self)
        return len(self.empty_cells) == len(self)

    def set_cell(self, cell: Cell, number: int) -> None:
        """Assigns a number to a Cell and updates `empty_cells`.
        """

        cell.number = number
        if number and (cell in self.empty_cells):
            self.empty_cells.remove(cell)
        elif not number and (cell not in self.empty_cells):
            self.empty_cells.add(cell)

    def set_point(self, key: Point, number: int) -> None:
        """Overrides a method of the base class. To assign a number to a Point
        is to change its Cell's number, not to replace the Cell with the
        number.
        This method is used by `BaseGameGrid` methods such as `__setitem__`.
        """

        self.set_cell(self[key], number)

    def seed(self, amount: int = STARTING_AMOUNT) -> None:
        """Assigns a number randomly chosen from `Grid.SEEDING_VALUES` to a
        few (`amount`) randomly selected empty Cells.
        """

        logger.debug(
            "Available cells for seeding: %s.",
            "  ".join(sorted(map(repr, self.empty_cells))),
        )
        changed: Set[Cell] = set()
        for cell in random.sample(self.empty_cells, amount):
            assert not cell  # must be 0
            self.set_cell(cell, random.choice(self.SEEDING_VALUES))
            changed.add(cell)
        logger.debug(
            "Seeded those cells: %s.", "  ".join(sorted(map(repr, changed))),
        )
        assert changed
        self.store_snapshot()

    def neighbor(self, cell: Cell, to: Directions) -> Optional[Cell]:
        """Returns the next (possibly empty) Cell in the given direction, or
        `None` if there"s none (if `self` is at the edge of the board,
        for example).
        """

        x, y = cell.point
        if to == Directions.LEFT:
            x -= 1
        elif to == Directions.RIGHT:
            x += 1
        elif to == Directions.DOWN:
            y += 1
        elif to == Directions.UP:
            y -= 1
        elif isinstance(to, Directions):
            # very bad
            raise ValueError(f"'to' must be {Directions.pretty()}, not {to!r}")
        else:
            # EVEN WORSE
            raise ExpectationError(to, Directions)
        try:
            next_point = Point(x, y)  # NegativeIntegerError
            next_cell = self[next_point]  # KeyError
        except (NegativeIntegerError, KeyError):
            return None
        assert isinstance(next_cell, type(cell))
        return next_cell

    def pivot(self, cell: Cell, to: Directions) -> Cell:
        """Returns the first non-empty, unlocked Cell in the given direction,
        including itself. If all Cells in this direction are empty, returns the
        one at the edge of the board instead.
        """

        current = last = cell
        while True:
            current = self.neighbor(current, to)
            if current is None:  # edge of the board; give up
                return last
            if not current:  # empty Cell; keep looking
                last = current
                continue
            if current.number == cell.number and not current.is_locked:
                return current
            # in this case, the new Cell's number matches, but it is locked
            # because it has already moved this cycle, so we ignore it
            return last

    def move_cell(self, cell: Cell, to: Directions) -> bool:
        """Attempts to move `cell` in the given `direction`. When successful,
        locks the pivot and updates the score (if the starting number was
        positive), then updates the numbers of the `cell` and its pivot.
        Returns whether movement ocurred.
        """

        if not cell:  # empty Cells don't move
            return False
        pivot = self.pivot(cell, to)
        if pivot == cell:
            return False
        new_number = cell.number + pivot.number
        # update the score only when the Cell moved to a positive pivot
        if pivot:
            pivot.lock()  # prevent further movement this cycle
            self.score += new_number
        self.set_cell(cell, 0)
        self.set_cell(pivot, new_number)
        return True

    def drag(self, to: Directions) -> bool:
        """If given a valid direction, increments its attempts count, then
        tries to move every cell in the given direction, starting with the
        vectors closest to it. If that changed anything, it increments its
        cycle by 1 and seeds itself by 1.
        """

        if to == Directions.LEFT:
            vectors = tuple(self.columns)
        elif to == Directions.RIGHT:
            vectors = tuple(self.columns)[::-1]
        elif to == Directions.UP:
            vectors = tuple(self.rows)
        elif to == Directions.DOWN:
            vectors = tuple(self.rows)[::-1]
        #
        self.attempt += 1
        logger.debug("Attempt increased to %d.", self.attempt)
        something_moved = False
        for cell in chain.from_iterable(vectors):
            this_moved = self.move_cell(cell, to)
            # assert isinstance(moved, bool)
            something_moved |= this_moved
        if something_moved:
            logger.debug("Dragging %r changed me.", to)
            self.cycle += 1
            logger.debug("Cycle increased to %d.", self.cycle)
            self.seed(1)  # will also store a snapshot
            for cell in self.cells():
                cell.unlock()
        return something_moved

    @property
    def is_jammed(self) -> bool:
        """Returns False if there's any legal movement left for the player,
        True if there's none.
        Rationale: if there's at least one zero Cell, the Grid is not jammed,
        because the player can at least fill the empty spot.
        If there are no zeroes, check if any two adjacent Cells have the same
        number; stop as soon as any such pair is found.
        Is there a better/faster way of doing this without checking every Cell?
        """

        if empties := len(self.empty_cells):
            logger.debug("Not jammed: still %d empty cell(s).", empties)
            return False
        for cell in self.cells():
            for to in Directions:
                neighbor = self.neighbor(cell, to)
                if neighbor is None:
                    continue
                if cell.number == neighbor.number:
                    logger.debug(
                        "Not jammed: %r is next to %r.", cell, neighbor,
                    )
                    return False
        logger.debug("Jammed grid detected!")
        return True

    def _autofill(self) -> None:
        numbers = self.NUMBERS[:-1]
        for cell in self.grid.cells():
            cell.unlock()
            self.set_cell(cell, random.choice(numbers))

    def autofill(self, no_jamming: bool = True) -> None:
        self._autofill()
        if no_jamming:
            while self.is_jammed:
                self._autofill()
        self.store_snapshot()
