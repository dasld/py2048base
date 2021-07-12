# -*- coding: utf-8 -*-
#
# tests.py
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

import sys
import unittest

from . import (
    APPNAME,
    VERSION,
    iscontainer,
    type_check,
    # Base2048Error,
    BaseGameGrid,
    # SquareGameGrid,
    # Directions,
    ExpectationError,
    # NegativeIntegerError,
    # Point,
)


class IntGameGrid(BaseGameGrid):
    CELLCLASS = int


class TestGenerics(unittest.TestCase):
    def test_iscontainer(self) -> None:
        class NewList(list):
            pass

        class NewString(str):
            pass

        sample = "sample"
        self.assertFalse(iscontainer(sample))
        self.assertFalse(iscontainer(NewString()))
        for iterable in (
            NewList(sample),
            list(sample),
            tuple(sample),
            set(sample),
        ):
            self.assertTrue(iscontainer(iterable))

    def test_type_check(self) -> None:
        # these shouldn't raise anything
        goods = [
            # single type
            (10, (complex, str), True),  # uncomment to fail a test!
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
            self.assertIsNone(type_check(obj, expectation, positive=boolean))
        for obj, expectation, boolean in bads:
            with self.assertRaises(ExpectationError):
                type_check(obj, expectation, positive=boolean)


if __name__ == "__main__":
    print(f"{__file__}: using {APPNAME} version {VERSION}")
    sys.exit(unittest.main())
