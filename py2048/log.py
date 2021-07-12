# -*- coding: utf-8 -*-
#
# log.py
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

import logging
import sys

from py2048 import APPNAME, DATA_DIR

__all__ = ["LOGGER", "setup_logger"]


# setup log folder and log file path
DATA_DIR.mkdir(exist_ok=True)
FPATH = str(DATA_DIR.resolve() / f"{APPNAME}.log")

# setup the default handlers
HANDLERS = (
    logging.FileHandler(filename=FPATH, mode="w"),
    logging.StreamHandler(stream=sys.stderr),
)
HANDLERS[-1].setLevel(logging.ERROR)  # will override the logger's level

# set up a formatter (to be used for all handlers)
FORMATTER = logging.Formatter(
    fmt="\t".join(
        [
            # "%(asctime)s,%(msecs)d",  # human-readable timestamp
            "%(asctime)s",  # human-readable timestamp
            # "%(name)s @ %(module)s",  # logger name @ module
            "%(funcName)s @ %(module)s",  # calling function @ module
            "(%(levelname)s) %(message)s",  # (level name) message
        ]
    ),
    datefmt="%H:%M:%S",
)


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    for h in HANDLERS:
        h.setFormatter(FORMATTER)
        logger.addHandler(h)
        logger.info("Loaded handler: '%s'.", h)
    logger.info("Created '%s'.", logger)
    return logger


# set up the main logger and equip it
LOGGER = setup_logger(APPNAME)
