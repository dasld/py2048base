# -*- coding: utf-8 -*-
#
# setup.py

import setuptools

from py2048 import _TESTING, APPNAME, VERSION


def readme() -> str:
    with open("README.rst", "r", encoding="utf-8") as rst:
        return rst.read()


setuptools.setup(
    name=f"{APPNAME}-danieldiniz" if _TESTING else f"{APPNAME}base",
    version=VERSION,
    author="Daniel Diniz",
    author_email="daniel_asl_diniz@protonmail.com",
    description="Python clone of the famous 2048 game.",
    long_description=readme(),
    long_description_content_type="text/x-rst",
    url="https://github.com/dasld/py2048base",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3.8",
        "Topic :: Games/Entertainment :: Puzzle Games",
    ],
    install_requires=["appdirs>=1"],
    packages=[APPNAME],
    python_requires=">=3.8",
    license="GPL",
    zip_safe=True,
)
