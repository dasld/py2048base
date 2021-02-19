#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# __main__.py
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

from typing import Any, Callable, List, NoReturn, Optional, Tuple

# logging will be configured by our 'log' module, unless "-q" has been passed
# from the command-line
import sys
from pathlib import Path
import argparse
import logging
from io import StringIO
from importlib import import_module

from py2048 import (  # alphabetical
    APPNAME,
    BUNDLE_DIR,
    COPY_FOOTER,
    IS_FROZEN,
    ModuleType,
    DEFAULT_FRONTENDS,
    ENTRY_POINT,
    VERSION,
)


## GLOBALS
CACHE = None  # will be initialized in `parse_arguments`
logger = None  # will be initialized in `setup_logger`


def parse_arguments() -> Tuple[List, List]:
    """Parses sys.argv options.
    """
    global CACHE
    CACHE = StringIO()
    CACHE.write(f"{sys.argv = !r}\n")

    cmd = APPNAME if IS_FROZEN else f"python3 -m {APPNAME}"

    mainparser = argparse.ArgumentParser(
        prog=cmd,
        description=(
            "Python implementation of the famous "
            "2048 game by Gabriele Cirulli. "
            "Many interfaces ('frontends') to play with are available."
        ),
        # allow_abbrev=False,
        epilog=COPY_FOOTER,
    )
    mainparser.add_argument(
        "frontend",
        metavar="frontend module name",
        # 'type' can take any callable that takes a single string argument and
        # returns the converted value
        # we don't use 'type=import_module' because it doesn't seem to be
        # interceptable by a try/except clause
        nargs="?",
        help=(
            "The frontend to play 2048 with. "
            f"A frontend is a Python module in {APPNAME}/frontends/ that "
            f"implements a '{ENTRY_POINT}' function."
        ),
    )
    mainparser.add_argument(
        "-g",
        "--goal",
        metavar="number",
        type=int,
        # no `default=2048` here; the default will be `None` and be handled
        # later
        help="the number of the tile needed to win",
    )
    verb_group = mainparser.add_mutually_exclusive_group()
    verb_group.add_argument(
        "-v",
        dest="verbosity",
        action="count",
        default=0,
        help="increase output verbosity",
    )
    verb_group.add_argument(
        "-q",
        "--quiet",
        dest="verbosity",
        action="store_const",
        const=None,
        help="suppress all logging",
    )
    mainparser.add_argument("--version", action="version", version=VERSION)
    # mainparser.add_argument("other", metavar="", nargs=argparse.REMAINDER)
    parseds, remainder = mainparser.parse_known_args()
    CACHE.write(f"{parseds = !r}\n")
    CACHE.write(f"{remainder = !r}\n")
    return parseds, remainder


def setup_logger(arguments) -> None:
    """Setup the logger (even if a dummy one).
    """
    global logger
    verbosity = arguments.verbosity
    if verbosity is not None:
        from py2048.log import logger

        # https://stackoverflow.com/a/5082809
        # less verbose <--> more verbose
        #   arg: 0  1  2  3  4  5
        # level: 50 40 30 20 10 0
        #        c  e  w  i  d  -
        levels = (logging.WARNING, logging.INFO, logging.DEBUG)
        try:
            logger.setLevel(levels[verbosity])
        except IndexError:
            logger.error(
                "verbosity cannot be negative or greater than %d",
                len(levels) - 1,
            )
            logger.setLevel(logging.WARNING)
    else:
        # setup a dummy logger
        logger = logging.getLogger(APPNAME)
        logger.addHandler(logging.NullHandler())
    # log previously cached messages
    CACHE.seek(0)  # read lines from the start
    for line in CACHE:
        line = line.strip()
        print(line)
        logger.info("Pre-logging message: %s", line)
    CACHE.close()


def chart_paths() -> None:
    logger.debug(f"{Path.cwd() = }")
    logger.debug(f"{Path(__file__) = }")
    logger.debug(f"{BUNDLE_DIR = }")


def load_frontend(name: str) -> Optional[ModuleType]:
    """Loads a single frontend and returns it.
    """

    try:
        return import_module(f"{APPNAME}.frontends.{name}")
    except ModuleNotFoundError:
        logger.exception("Failed to import module %r.", name)


def load_default_frontend() -> Optional[ModuleType]:
    """Iterates over the DEFAULT_FRONTENDS list and returns the first to be
    successfully imported.
    """

    for name in DEFAULT_FRONTENDS:
        front = load_frontend(name)
        if front:
            return front
    return None


def get_frontend(arguments) -> Optional[ModuleType]:
    chosen = None
    asked = arguments.frontend
    if asked:
        if asked in DEFAULT_FRONTENDS:
            DEFAULT_FRONTENDS.remove(asked)
        chosen = load_frontend(asked)
    if not chosen:
        # user choice didn't work or wasn't given, fallback
        chosen = load_default_frontend()
    return chosen


def get_subparser(module: ModuleType) -> Optional[Any]:
    subparsers = [
        value
        for value in vars(module).values()
        if hasattr(value, "parse_args")
        # if isinstance(value, argparse.ArgumentParser)
    ]
    if not subparsers:
        return None
    if amount := len(subparsers) > 1:
        logger.critical(
            "%s expects no parser or exactly one parser in each frontend, but "
            "%d have been found",
            APPNAME,
            amount,
        )
        sys.exit(1)
    return subparsers[0]


def call_and_exit(fun: Callable, *args, **kwargs) -> NoReturn:
    try:
        fun(*args, **kwargs)
    except BaseException as error:
        logger.critical(str(error))
        sys.exit(1)
    sys.exit()


def main() -> NoReturn:
    parseds, remainder = parse_arguments()
    setup_logger(parseds)
    chart_paths()
    frontend = get_frontend(parseds)
    if not frontend:
        logger.critical(
            "No frontend could be loaded, not even the default ones; aborting."
        )
        sys.exit(1)
    logger.info("Parsed frontend: %s", frontend.__name__)
    try:
        entry_point = getattr(frontend, ENTRY_POINT)
    except AttributeError:
        logger.critical(
            "A %r frontend must provide a %r function", APPNAME, ENTRY_POINT,
        )
        sys.exit(1)
    # subparse remaining arguments
    subparser = get_subparser(frontend)
    if not subparser:
        # no parser in this frontend; is this a problem?
        if remainder:
            # it's a problem, because there was some stuff left to parse
            logger.critical(
                "No parser in %s, but command-line arguments provided: %r",
                (frontend, remainder),
            )
            sys.exit(1)
    else:
        # a subparser has been found in the frontend
        # the frontend must know the desired goal for the initial run
        # since this information concerns the whole game and not a particular
        # display of it, we attribute it in the main parser and then pass it
        # to eventual frontend subparsers
        sub_class = type(subparser).__name__
        logger.debug(
            "Subparser %r of type %s found in %s",
            subparser,
            sub_class,
            frontend,
        )
        play_kwargs = {"goal": parseds.goal}
        try:
            # parse remaining command-line arguments, if any
            remainder_dict = vars(subparser.parse_args(remainder))
            play_kwargs.update(remainder_dict)
        except AttributeError:
            logger.critical(
                "%r, if it exists, must implement a 'parse_args' "
                "method, like 'argparse.ArgumentParser' objects; "
                "the parser found is of type %s",
                parser,
                sub_class,
            )
            sys.exit(1)
    # input("would call 'call_and_exit(entry_point, **play_kwargs)' here")
    try:
        call_and_exit(entry_point, **play_kwargs)
    except NameError:
        call_and_exit(entry_point)


if __name__ == "__main__":
    main()
