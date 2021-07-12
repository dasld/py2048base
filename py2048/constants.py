# -*- coding: utf-8 -*-
#
# constants.py
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

"""Declares a few "constants" that aren't that important to the rest of the
package. Most are just for type-hinting and type annotations.
"""

import enum
from typing import TYPE_CHECKING, Sequence, Type, Union


# https://github.com/python/cpython/blob/ebe20d9e7eb138c053958bc0a3058d34c6e1a679/Lib/types.py#L51
ModuleType = type(enum)  # just for annotation purposes
Vector = Sequence[int]
Expectation = Union[Type, Sequence[Type]]

# annotating Ellipsis seems to be way more painful than it should >:(
# the only solution I could find is what Guido posted here:
# https://github.com/python/typing/issues/684#issuecomment-548203158
if TYPE_CHECKING:

    class EllipsisType(enum.Enum):
        Ellipsis = "..."

    Ellipsis = EllipsisType.Ellipsis
else:
    EllipsisType = type(Ellipsis)

# I use these "constants" because I find them a bit more readable than
# writing `slice(None)` or `()` everytime
#
# this is used in __init__.BaseGameGrid.check_integrity
EMPTY_TUPLE = tuple()
#
# this is used in __init__.GridIndex
NONE_SLICE = slice(None)
