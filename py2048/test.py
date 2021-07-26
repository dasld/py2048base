# -*- coding: utf-8 -*-
#
# test.py
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

"""pytest test suite.

To run, simply:
>>> pytest-3 py2048/test.py
"""

# allowing postponed evaluation of annotations; see:
# https://www.python.org/dev/peps/pep-0563/
from __future__ import annotations

import random
import sys

import pytest

from .core import BaseGameGrid, Point
from .utils import (
    ExpectationError,
    NegativeIntegerError,
    classname,
    either_0_power2,
    is_container,
    type_check,
)


class TestUtils:
    _BIG_NUMBER = 3_000
    _POWERS2 = {
        _BIG_NUMBER: {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048},
    }

    def test_classname(self) -> None:
        for name in ("_Foo", "_Bar", "_Baz"):
            exec(f"class {name}: pass")  # create a class
            cls = locals()[name]
            instance = cls()
            assert name == classname(cls) == classname(instance)

    def test_either_0_power2(self) -> None:
        big_number = self._BIG_NUMBER
        powers = {n for n in range(big_number) if either_0_power2(n)}
        assert powers == self._POWERS2[big_number]

    def test_iscontainer(self) -> None:
        class NewList(list):
            pass

        class NewString(str):
            pass

        sample = "sample"
        for string in (
            sample,
            NewString(sample),
            "",
        ):
            assert not is_container(string)
        for iterable in (
            NewList(sample),
            list(sample),
            tuple(sample),
            set(sample),
            frozenset(sample),
        ):
            assert is_container(iterable)

    def test_type_check(self) -> None:
        # these shouldn't raise anything
        goods = [
            # single type
            # (10, (complex, str), True),  # uncomment to fail a test!
            (3, int, True),
            (3, str, False),
            ("3", str, True),
            # 2+ types
            (3, (complex, float, int), True),
            (3, (str, bytes, tuple), False),
            ("3", (int, str), True),
        ]
        # these should raise ExpectationError
        bads = [
            # single type
            (3, str, True),
            ("3", str, False),
            ([], tuple, True),
            # 2+ types
            (4.0, (list, str), True),
            (4, (float, int), False),
            ([], (str, tuple), True),
        ]

        for obj, expectation, boolean in goods:
            assert type_check(obj, expectation, was_positive=boolean) is None
        for obj, expectation, boolean in bads:
            with pytest.raises(ExpectationError):
                type_check(obj, expectation, was_positive=boolean)


class TestPoint:
    def test_point(self) -> None:
        # test type problems
        for obj in (str(), float(), complex(), tuple()):
            with pytest.raises(ExpectationError):
                Point(obj, obj)
        # test value problems
        for i in range(1, 10):
            good_point = Point(i, i)
            assert isinstance(good_point, Point)
            bad_coordinates = [(-i, i), (i, -i), (-i, -i)]
            for x, y in bad_coordinates:
                with pytest.raises(NegativeIntegerError):
                    Point(x, y)


class IntGameGrid(BaseGameGrid):
    CELLCLASS = int

    @classmethod
    def _make_ranged(cls, cols, rows) -> IntGameGrid:
        """Populate a grid in "low level", that is, using only the
        methods of its inner dictionary of points.

        It's numbered in a Z shape: left to right, then top to bottom.
        """

        new = cls(cols, rows)
        counter = 0
        for r in range(rows):
            for c in range(cols):
                new.mapping[Point(c, r)] = counter
                counter += 1
        return new

    def _shuffle(self) -> None:
        pool = list(self.mapping.values())
        for point, current in self.mapping.items():
            # random.randint includes both boundaries
            i = random.randint(0, len(pool) - 1)
            while pool[i] == current:
                i = random.randint(0, len(pool) - 1)
            self.mapping[point] = pool.pop(i)
        if pool:
            sys.exit("IntGameGrid._shuffle didn't work as expected; aborting.")


class TestIntGameGrid:
    # each method in a pytest receives
    # a different instance of the test class
    # https://pytest.org/en/latest/getting-started.html
    SMALL_NUMBER = 40
    BIG_NUMBER = 60

    @staticmethod
    def _index_columns(grid: IntGameGrid, cols: int) -> None:
        """Ensure the grid columns can be indexed for reading."""

        # keep a copy of the values due to another loop in this method
        cells = []
        for i, col in enumerate(grid.columns()):
            assert grid[i] == col
            for j, cell in enumerate(col):
                assert cell == (j * cols) + i
                cells.append(cell)
        #
        for colA, colB in zip(
            grid.columns(reverse=True), reversed(list(grid.columns()))
        ):
            assert colA == colB
        #
        for cell, number in zip(grid.values(by="column"), cells):
            assert cell == number
        # try bad indexes
        for bad in range(30):
            with pytest.raises(KeyError):
                grid[cols + bad]

    @staticmethod
    def _index_rows(grid: IntGameGrid, cols: int, rows: int) -> None:
        """Ensure the grid rows can be indexed for reading."""

        cells = cols * rows
        assert cells == len(grid.mapping)
        for i, row in enumerate(grid.rows()):
            assert grid[..., i] == row
            for j, cell in enumerate(row):
                assert cell == (i * cols) + j
        # check the points accessed directly by rows match the Z shape
        for cell, number in zip(grid.values(by="row"), range(cells)):
            assert cell == number
        # try bad indexes
        for bad in range(30):
            with pytest.raises(KeyError):
                grid[..., rows + bad]

    def test_grid_indexing(self) -> None:
        big, small = self.BIG_NUMBER, self.SMALL_NUMBER

        wide = IntGameGrid._make_ranged(big, small)
        tall = IntGameGrid._make_ranged(small, big)

        for grid, cols, rows in (
            (wide, big, small),
            (tall, small, big),
        ):
            self._index_columns(grid, cols)
            self._index_rows(grid, cols, rows)
