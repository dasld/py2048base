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

# allowing postponed evaluation of annotations; see:
# https://www.python.org/dev/peps/pep-0563/
from __future__ import annotations

import logging
import random
import sys
from itertools import chain
from typing import (
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Type,
)

from py2048 import (
    Base2048Error,
    SquareGameGrid,
    Directions,
    ExpectationError,
    Line,
    NegativeIntegerError,
    Point,
    Snapshot,
    classname,
)
from py2048.cell import Cell


logger = logging.getLogger(__name__)


class Grid(SquareGameGrid):
    CELLCLASS = Cell
    # how many Cells start non-zero
    STARTING_AMOUNT = 2
    # what values can be seeded in each Cell; tuple instead of set because
    # random.choice doesn't work with sets
    SEEDING_VALUES = (2, 4)
    # the `is2048like` method will use this list to validate a goal
    # 2**11 == 2048
    NUMBERS: List[int] = [2 ** power for power in range(1, 12)]
    # _AUTO_NUMBERS is used to autofill the grid (for testing and debugging)
    _AUTO_NUMBERS = NUMBERS[:-1]
    # no power of 2 higher than CEILING will be accepted as the game's goal
    # sys.maxsize == (2**63)-1 on 64bits machines
    CEILING = sys.maxsize
    SHIFTS = {
        Directions.LEFT: (-1, 0),
        Directions.RIGHT: (1, 0),
        Directions.DOWN: (0, 1),
        Directions.UP: (0, -1),
    }

    cells = SquareGameGrid.values

    @classmethod
    def is2048like(cls, number: int) -> bool:
        """Tell whether `number` is a positive power of 2 no greater than
        `cls.CEILING`.

        :param int number: the integer to check
        :return: either valid or invalid
        """

        highest = cls.NUMBERS[-1]
        assert highest == max(cls.NUMBERS)
        while number > highest:
            highest *= 2
            if highest >= cls.CEILING:
                break
            cls.NUMBERS.append(highest)
        return number in cls.NUMBERS

    def __init__(self, side: int = 4, storing_snapshot: bool = True) -> None:
        logger.info("Creating a %dx%d Grid instance", side, side)
        if self.STARTING_AMOUNT < 1:
            raise Base2048Error(
                "Cannot create a 2048 grid with less than 1 STARTING_AMOUNT"
            )
        side_squared = side * side
        if self.STARTING_AMOUNT > side_squared:
            raise Base2048Error(
                "Cannot create a 2048 grid with more than "
                f"{side_squared} STARTING_AMOUNT's"
            )
        super().__init__(side)
        self._vectors_getters = {
            Directions.LEFT: (self.columns, False),
            Directions.RIGHT: (self.columns, True),
            Directions.UP: (self.rows, False),
            Directions.DOWN: (self.rows, True),
        }
        # the grid starts empty, so every Cell starts in the `empty_cells` set
        self.empty_cells: Set[Cell] = set(self.cells())
        self.history: List[Snapshot] = []
        # `attempt` is how many times the player has given input, even if that
        # didn't change the game state
        self.attempt = 0
        # `cycle` is how many times the game state has changed
        self.cycle = 0
        # `score` is a counter that increases by N each time an N-numbered Cell
        # is formed
        self.score = 0
        # the grid could start jammed if self.STARTING_AMOUNT == side ** 2
        if self.is_jammed:
            self.autofill()  # will also store a snapshot
        elif storing_snapshot:
            self.store_snapshot()
        self.check_integrity()

    def reset(self) -> None:
        """Set all counters and Cells to 0 and clear the snapshots history.

        Also unlock every Cell.
        """

        self.attempt = 0
        self.cycle = 0
        self.score = 0
        for cell in self.cells():
            cell.unlock()
            self.set_cell(cell, 0)
        self.history.clear()
        self.check_integrity()

    def store_snapshot(self, snapshot: Optional[Snapshot] = None) -> None:
        """Store a game state in `history`.

        If `snapshot` isn't provided, it defaults to the current game state.
        """

        if snapshot is None:
            snapshot = {point: cell.number for point, cell in self.items()}
        self.history.append(snapshot)

    def update_with_snapshot(self, snapshot: Snapshot) -> None:
        """Replace each Cell number with the corresponding `snapshot` value.

        Also unlock every Cell. This DOESN'T store the snapshot.
        """

        for point, number in snapshot.items():
            cell = self[point]
            cell.unlock()
            self.set_cell(cell, number)
        self.check_integrity()

    @classmethod
    def new_from_snapshot(cls, snapshot: Snapshot) -> Grid:
        """Return a new Grid with the values of `snapshot`.
        """

        sqrt = len(snapshot) ** 0.5  # a float
        side = int(sqrt)
        if side != sqrt:
            name = classname(cls)
            raise ValueError(f"Cannot create {name} from a non-square mapping")
        new = cls(side, storing_snapshot=False)
        new.update_with_snapshot(snapshot)
        new.store_snapshot()
        return new

    def undo(self, ignore_empty: bool = True) -> bool:
        """Try to restore the game to its previous state.

        :param bool ignore_empty: whether to ignore a lack of snapshots
        :return: whether undoing occurred
        """

        if len(self.history) >= 2:
            # the last snapshot is the current state, so we forget it
            del self.history[-1]
            # now the last snapshot is the previous state, so we retrieve and
            # forget it
            past = self.history.pop()
        else:
            if not ignore_empty:
                raise IndexError(
                    "cannot undo last movement: too few snapshots available"
                )
            return False
        self.update_with_snapshot(past)
        self.store_snapshot(past)
        return True

    @property
    def largest(self) -> int:
        return max((cell.number for cell in self.cells()), default=0)

    @property
    def is_empty(self) -> bool:
        """Return whether every Cell is empty (ie, 0-numbered).
        """

        empties, cells = len(self.empty_cells), len(self)
        assert empties <= cells
        return empties == cells

    def set_cell(self, cell: Cell, number: int) -> None:
        """Assign `number` to `Cell` and update `empty_cells`.
        """

        cell.number = number
        if number:
            # `discard` removes an element from a set but doesn't raise an
            # exception if it wasn't present
            self.empty_cells.discard(cell)
        else:
            self.empty_cells.add(cell)

    def set_point(self, key: Point, number: int) -> None:
        """Assign `number` to the Cell at `key`.

        This overrides a base class method. To assign a number to a Point
        is to change its Cell's number, not to replace the Cell with the
        number!
        This method is used by `BaseGameGrid` methods such as `__setitem__`.
        """

        self.set_cell(self[key], number)

    def seed(self, amount: int = STARTING_AMOUNT) -> None:
        """Assign a random integer from `Grid.SEEDING_VALUES` to randomly
        selected empty Cells.

        :param int amount: how many cells to seed;
            defaults to `STARTING_AMOUNT`
        """

        logger.debug(
            "Available cells for seeding: %s.",
            "  ".join(map(repr, sorted(self.empty_cells))),
        )
        changed: List[Cell] = []
        for cell in random.sample(self.empty_cells, amount):
            if cell:
                raise Base2048Error(
                    "A non-zero Cell has been selected for seeding"
                )
            self.set_cell(cell, random.choice(self.SEEDING_VALUES))
            changed.append(cell)
        if not changed:
            raise Base2048Error("Seeding didn't change the number of any Cell")
        changed.sort()
        logger.debug(
            "Seeded those cells: %s.", "  ".join(map(repr, changed)),
        )
        self.store_snapshot()

    def neighbor(self, cell: Cell, to: Directions) -> Optional[Cell]:
        """Return the next Cell in the given direction.

        This returns `None` if there's no such Cell (if `cell` is at the edge
        of the board, for example).
        """

        x, y = cell.point + self.SHIFTS[to]
        try:
            next_point = Point(x, y)  # NegativeIntegerError
            next_cell = self[next_point]  # KeyError
        except (NegativeIntegerError, KeyError):
            return None
        assert isinstance(next_cell, type(cell))
        return next_cell

    def pivot(self, cell: Cell, to: Directions) -> Cell:
        """Return either `cell` itself, or the cell that it will interact with.

        This never returns `None`. It will return either:
        i) the first unlocked Cell with a matching number; or
        ii) the last empty Cell in direction `to`, if there's any; or
        iii) `cell` itself.

        Remember that "Cell_X is empty" means `Cell_X.number == 0`.
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
            # in this case, either:
            # i) this Cell's number doesn't match; or
            # ii) this Cell's number matches, but it's locked because it has
            #     already moved this cycle
            return last

    def move_cell(self, cell: Cell, to: Directions) -> bool:
        """Attempt to move `cell` in direction `to`.

        When successful, lock the pivot and update the score (if the starting
        number was positive), then update the numbers of the `cell` and of its
        pivot.

        :return: whether movement occurred
        """

        if not cell:  # empty Cells don't move
            return False
        pivot = self.pivot(cell, to)
        if pivot == cell:  # a Cell can't move into itself
            return False
        # we can't use `cell.number * 2` or `pivot.number * 2` because
        # the numbers differ when a positive Cell moves into a 0 one
        new_number = cell.number + pivot.number
        # in the original game the score only increases when a Cell moves into
        # a positive pivot
        if pivot:
            pivot.lock()  # prevent further movement this cycle
            self.score += new_number
        self.set_cell(cell, 0)
        self.set_cell(pivot, new_number)
        return True

    def _vectors_from_Directions(self, to: Directions) -> Iterator[Line]:
        """Return each row or column, from closest to farthest from `to`.
        """

        try:
            method, reverse_boolean = self._vectors_getters[to]
        except KeyError:
            if isinstance(to, Directions):
                # very bad
                raise ValueError(
                    f"'to' must be {Directions.pretty()}, not {to!r}"
                )
            else:
                # EVEN WORSE
                raise ExpectationError(to, Directions)
        return method(reverse=reverse_boolean)

    def drag(self, to: Directions) -> bool:
        """Try to move every Cell towards `to`, starting with the vectors
        closest to the origin.

        Increment the attempt counter, then try to move every Cell in the
        given direction, starting with the vectors closest to the origin.
        If that changed anything, increment the cycle counter by 1 and seed
        itself by 1.

        :return: whether the game state changed
        """

        vectors = self._vectors_from_Directions(to)
        self.attempt += 1
        logger.debug("Attempt increased to %d.", self.attempt)
        something_moved = False
        for cell in chain.from_iterable(vectors):
            this_moved = self.move_cell(cell, to)
            something_moved = something_moved or this_moved
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
        """Tell whether there's any legal movement left for the player.

        If there's at least one zero `Cell`, the `Grid` isn't jammed, because
        the player can at least fill the blank.
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
        for cell in self.cells():
            cell.unlock()
            self.set_cell(cell, random.choice(self._AUTO_NUMBERS))

    def autofill(self, no_jamming: bool = True) -> None:
        """Give each Cell a random number.

        Store a snapshot afterwards. The numbers are always greater than 0 and
        smaller than 2048.
        Also, unlock every Cell.

        :param bool no_jamming: if the result cannot be a jammed grid
        """

        self._autofill()
        if no_jamming:
            while self.is_jammed:
                self._autofill()
        self.store_snapshot()
