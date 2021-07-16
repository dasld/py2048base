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

# these basic "constants" are declared here before imports because
# other modules we import require them, so we're avoiding circular
# importing errors
_TESTING = False  # used only in setup.py
__version__ = (0, 44)
VERSION = ".".join(map(str, __version__))
APPNAME = __name__

from py2048.basefrontend import Base2048Frontend
from py2048.cell import Cell
from py2048.core import (
    DATA_DIR,
    BaseGameGrid,
    Directions,
    Point,
    SquareGameGrid,
)
from py2048.grid import Grid
from py2048.log import setup_logger
from py2048.utils import (
    Base2048Error,
    ExpectationError,
    InvalidCellIntError,
    NegativeIntegerError,
    check_int,
    classname,
    either_0_power2,
    hexid,
    is_container,
    type_check,
    typename,
)
