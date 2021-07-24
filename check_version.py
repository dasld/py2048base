#!/usr/bin/env -S python3 -I
# -*- coding: utf-8 -*-
#
# check_version.py

"""Prints the local py2048 version iff it's greater than the installed
py2048 version.

* IMPORTANT *
Run this as:
>>> python3 -I check_version.py

The -I flag keeps Python from adding the current directory to sys.path:
we want to import the installed version of py2048, not the local one.
https://docs.python.org/3/using/cmdline.html#id2
"""

import sys
from py2048 import __version__ as global_version, APPNAME


def get_local_version():
    version_line = None
    with open(f"./{APPNAME}/__init__.py") as init:
        for line in init:
            if line.startswith("__version__"):
                version_line = line
                break
    if not version_line:
        sys.exit(f"Couldn't find '__version__'; aborting.")
    return eval(version_line.split("=")[-1].strip())


if __name__ == "__main__":
    if not sys.flags.isolated:
        my_name = sys.argv[0]
        sys.exit(f"{my_name} must be run with the '-I' flag; aborting.")
    local = get_local_version()
    if local > global_version:
        print(local, end="")
