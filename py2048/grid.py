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
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    cast,
)

from py2048 import (
    SquareGameGrid,
    Directions,
    Line,
    Point,
    Snapshot,
)
from py2048.cell import Cell
from py2048.utils import (
    Base2048Error,
    ExpectationError,
    NegativeIntegerError,
    classname,
)

"""Declares the `Grid` class.
"""

logger = logging.getLogger(__name__)


class Grid(SquareGameGrid):
    """Matrix of `Cell`s.

    This class is responsible for merging Cells into each other and
    recording game states, so that the user can "undo" their last
    input.
    It's not intended to display the game state, although `__str__`
    returns each row in a separate line.

    Main ("public") methods:

    drag(self, to: Directions) -> bool
        Attempts to move each Cell towards the given Direction, starting with
        the ones closest to that direction (that is, trying to move left picks
        the columns from left to right, trying to move right picks columns
        from right to left, and so on).
    undo(self, ignore_empty: bool = True) -> bool
        Restore the game to its last state.
    """

    # -- "public" class variables
    CELLCLASS = Cell
    # how many Cells start non-zero
    STARTING_AMOUNT = 2
    # what values can be seeded in each Cell; tuple instead of set because
    # random.choice doesn't work with sets
    SEEDING_VALUES = (2, 4)
    # the `is2048like` method will use this list to validate a goal
    # 2**11 == 2048
    NUMBERS: List[int] = [2 ** power for power in range(1, 12)]
    # no power of 2 higher than CEILING will be accepted as the game's goal
    # sys.maxsize == (2**63)-1 on 64bits machines
    CEILING = sys.maxsize
    cells = SquareGameGrid.values

    # -- "private" class variables
    # _AUTO_NUMBERS is used to fill the grid with random numbers
    # (for testing and debugging)
    _AUTO_NUMBERS = NUMBERS[:-1]
    # _SHIFTS maps each `Directions` into a x-y "displacement";
    # so `LEFT: (-1, 0)` means that
    # to be at the left of (x, y) is to be at (x-1, y), which may or may be not
    # valid coordinates for a Point
    _SHIFTS = {
        Directions.LEFT: (-1, 0),
        Directions.RIGHT: (1, 0),
        Directions.DOWN: (0, 1),
        Directions.UP: (0, -1),
    }

    # -- init
    def __init__(self, side: int = 4) -> None:
        # this creates an empty Grid; to create one from some other initial
        # state, use `Grid.new_from_snapshot`
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
        # as the grid starts empty, every Cell starts in the `empty_cells` set
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
        # do not store a snapshot in this case: the player shouldn't be able to
        # "undo" the grid until it's totally empty!
        self.check_integrity()

    # -- "private" methods
    def _set_point(self, key: Point, number: int) -> None:
        """Assign `number` to the Cell at `key` and update `empty_cells`.

        This overrides a base class method. To assign a number to a Point
        is to change its Cell's number, not to replace the Cell with the
        number!
        This method is used by `BaseGameGrid` methods such as `__setitem__`.
        """

        self._set_cell(self[key], number)

    def _set_cell(self, cell: Cell, number: int) -> None:
        """Assign `number` to `Cell` and update `empty_cells`.
        """

        cell.number = number
        if number:
            # `discard` removes an element from a set but doesn't raise an
            # exception if it wasn't present
            self.empty_cells.discard(cell)
        else:
            self.empty_cells.add(cell)

    def _neighbor(self, cell: Cell, to: Directions) -> Optional[Cell]:
        """Return the next Cell in the given direction.

        This returns `None` if there's no such Cell (if `cell` is at the edge
        of the board, for example).
        """

        x, y = cell.point + self._SHIFTS[to]
        try:
            next_point = Point(x, y)  # NegativeIntegerError
            next_cell = self[next_point]  # KeyError
        except (NegativeIntegerError, KeyError):
            return None
        assert isinstance(next_cell, type(cell))
        return next_cell

    def _pivot(self, cell: Cell, to: Directions) -> Cell:
        """Return either `cell` itself, or the Cell it will interact with.

        This never returns `None`. It returns either:
        i) the first unlocked Cell with a matching number; or
        ii) the last empty Cell in direction `to`, if there's any; or
        iii) `cell` itself.

        Remember that "CellX is empty" means `CellX.number == 0`.
        """

        current = last = cell
        target = cell.number
        while True:
            current = self._neighbor(current, to)
            # a 0-numbered Cell is falsy, so explicitly check for None
            if current is None:  # edge of the board; give up
                return last
            if not current:  # empty Cell; keep looking
                last = current
                continue
            if current.number == target and not current.is_locked:
                return current
            # in this case, the Cell exists and isn't empty, but is bad
            return last

    def _move_cell(self, cell: Cell, to: Directions) -> bool:
        """Attempt to move `cell` in direction `to`.

        When successful, lock the pivot and update the score (if the starting
        number was positive), then update the numbers of the `cell` and of its
        pivot.

        :return: whether movement occurred
        """

        if not cell:  # empty Cells don't move
            return False
        pivot = self._pivot(cell, to)
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
        self._set_cell(cell, 0)
        self._set_cell(pivot, new_number)
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

    def _autofill(self) -> None:
        for cell in self.cells():
            cell.unlock()
            self._set_cell(cell, random.choice(self._AUTO_NUMBERS))

    @staticmethod
    def _check_snapshot(snapshot: Snapshot) -> None:
        """Ensure a given snapshot has at least one positive value.
        """

        if not any(snapshot.values()):
            raise ValueError(f"Cannot record an empty snapshot: {snapshot}")

    # -- "public" methods
    # these are the methods expected to be called from outside this class,
    # especially by Base2048Frontend and its possible subclasses
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

    def reset(self) -> None:
        """Set all counters and Cells to 0 and clear the snapshots history.

        Also unlock every Cell.
        """

        self.attempt = 0
        self.cycle = 0
        self.score = 0
        for cell in self.cells():
            cell.unlock()
            self._set_cell(cell, 0)
        self.history.clear()
        self.check_integrity()

    def store_snapshot(self, snapshot: Optional[Snapshot] = None) -> None:
        """Store a game state in `history`.

        If `snapshot` isn't provided, it defaults to the current game state.
        """

        if snapshot is None:
            snapshot = {point: cell.number for point, cell in self.items()}
        self._check_snapshot(snapshot)
        self.history.append(snapshot)

    def update_with_snapshot(self, snapshot: Snapshot) -> None:
        """Replace each Cell number with the corresponding `snapshot` value.

        Also unlock every Cell. This DOESN'T store a snapshot.
        """

        self._check_snapshot(snapshot)
        for point, number in snapshot.items():
            cell = self[point]
            cell.unlock()
            self._set_cell(cell, number)
        self.check_integrity()

    @classmethod
    def new_from_snapshot(cls, snapshot: Snapshot) -> Grid:
        """Return a new Grid with the values of `snapshot`.
        """

        # snapshots should be squares, so a snapshot with k cells will have
        # side sqrt(k)
        sqrt = len(snapshot) ** 0.5  # a float
        side = int(sqrt)
        if side != sqrt:
            name = classname(cls)
            raise ValueError(f"Cannot create {name} from a non-square mapping")
        new = cls(side)
        new.update_with_snapshot(snapshot)
        new.store_snapshot(snapshot)
        return new

    def undo(self, ignore_empty: bool = True) -> bool:
        """Try to restore the game to its previous state.

        :param bool ignore_empty: whether to ignore a lack of snapshots
        :return: whether undoing occurred
        """

        if len(self.history) < 2:
            if not ignore_empty:
                raise IndexError(
                    "Cannot undo last movement: too few snapshots available"
                )
            return False
        # the last snapshot is the current state, so we forget it
        del self.history[-1]
        # now the last snapshot is the previous state, so we retrieve and
        # keep it stored, because it is now the current state
        self.update_with_snapshot(self.history[-1])
        return True

    @property
    def largest(self) -> int:
        return max((cell.number for cell in self.cells()), default=0)

    @property
    def is_empty(self) -> bool:
        """Return whether every Cell is empty (ie, 0-numbered).
        """

        empties, cells = len(self.empty_cells), len(self)
        assert empties <= cells, f"{self!r} has more empty Cells than Cells!"
        return empties == cells

    def seed(self, amount: int = STARTING_AMOUNT) -> None:
        """Assign a random integer from `Grid.SEEDING_VALUES` to randomly
        selected empty Cells.

        :param int amount: how many cells to seed;
            defaults to `STARTING_AMOUNT`
        """

        logger.debug(
            "Available cells for seeding: %s.",
            "  ".join(
                repr(e) for e in sorted(cast(Iterable, self.empty_cells))
            ),
        )
        changed: List[Cell] = []
        for cell in random.sample(self.empty_cells, amount):
            if cell:
                raise Base2048Error(
                    "A non-zero Cell has been selected for seeding"
                )
            self._set_cell(cell, random.choice(self.SEEDING_VALUES))
            changed.append(cell)
        if not changed:
            raise Base2048Error("Seeding didn't change the number of any Cell")
        changed.sort()
        logger.debug(
            "Seeded those cells: %s.", "  ".join(map(repr, changed)),
        )
        self.store_snapshot()

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
            this_moved = self._move_cell(cell, to)
            something_moved = something_moved or this_moved
        if something_moved:
            self.cycle += 1
            self.seed(1)  # will also store a snapshot
            for cell in self.cells():
                cell.unlock()
            logger.debug(
                "Dragging %r changed me; cycle increased to %d.", to, self.cycle
            )
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
                neighbor = self._neighbor(cell, to)
                if neighbor is None:
                    continue
                if cell.number == neighbor.number:
                    logger.debug(
                        "Not jammed: %r is next to %r.", cell, neighbor,
                    )
                    return False
        logger.debug("Jammed grid detected!")
        return True

    def autofill(self, no_jamming: bool = True) -> None:
        """Give each Cell a random number.

        Store a snapshot afterwards. The numbers are always greater than 0 and
        smaller than 2048.
        Also, unlock every Cell.

        :param bool no_jamming: if the result cannot be a jammed grid
        """

        # maybe Python should have "do-while" loops...
        self._autofill()
        if no_jamming:
            while self.is_jammed:
                self._autofill()
        self.store_snapshot()
