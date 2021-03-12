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
    # Any,
    Optional,
    Set,
    Tuple,
)
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


class Grid(SquareGameGrid):
    CELLCLASS: type = Cell
    # how many cells start non-zero
    STARTING_AMOUNT = 2
    # what values can be seeded in each cell
    SEEDING_VALUES = (2, 4)

    cells = SquareGameGrid.values

    def __init__(self, side: int = 4) -> None:
        logger.info("Creating a %dx%d Grid instance", side, side)
        assert 0 < self.STARTING_AMOUNT < side ** 2
        super().__init__(side)
        self.empty_cells: Set[Cell] = set(self.cells())
        self.reset(on_init=True)

    def reset(self, on_init: bool = False) -> None:
        self.attempt = 0
        self.cycle = 0
        self.score = 0
        if not on_init:
            for cell in self.cells():
                if cell:
                    cell.unlock()
                    self.set_cell(cell, 0)
        self.check_integrity()

    @property
    def largest_number(self) -> int:
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
        # return tuple(changed)

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
        else:
            raise ValueError(f"'to' must be {Directions.pretty()}, not {to!r}")
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
            if current.number == cell.number and not current.locked:
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
        if pivot:
            pivot.lock()  # prevent further movement this cycle
            # update the score only when the Cell moved to a positive pivot
            self.score += new_number
        self.set_cell(cell, 0)
        self.set_cell(pivot, new_number)
        return True

    def drag(self, to: Directions) -> bool:
        """Increments its attempts count, then tries to move every cell in the
        given direction, starting with the vectors closest to this direction.
        If anything changed, it increments its cycle by 1 and seeds itself by
        1.
        """

        if to == Directions.LEFT:
            vectors = tuple(self.columns)
        elif to == Directions.RIGHT:
            vectors = tuple(self.columns)[::-1]
        elif to == Directions.UP:
            vectors = tuple(self.rows)
        elif to == Directions.DOWN:
            vectors = tuple(self.rows)[::-1]
        elif isinstance(to, Directions):
            # very bad
            raise ValueError(f"'to' must be {Directions.pretty()}, not {to!r}")
        else:
            # EVEN WORSE
            raise ExpectationError(to, Directions)
        something_moved = False
        self.attempt += 1
        logger.debug("Attempt increased to %d.", self.attempt)
        for cell in chain.from_iterable(vectors):
            this_moved = self.move_cell(cell, to)
            # assert isinstance(moved, bool)
            if not something_moved and this_moved:
                something_moved = True
        if something_moved:
            logger.debug("Dragging %r changed me.", to)
            self.cycle += 1
            logger.debug("Cycle increased to %d.", self.cycle)
            self.seed(1)
            for cell in self.cells():
                if cell:
                    cell.unlock()
        return something_moved

    @property
    def jammed(self) -> bool:
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
        logger.debug("JAMMED!")
        return True
