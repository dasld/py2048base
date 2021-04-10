######
py2048
######

.. image:: https://img.shields.io/github/license/dasld/py2048base?color=blue&style=flat-square   :alt: GitHub
.. image:: https://img.shields.io/pypi/v/py2048base?color=green&style=flat-square   :alt: PyPI

**py2048** is a clone of the famous game
`2048 <https://play2048.co/>`_,
by
`Gabriele Cirulli <http://gabrielecirulli.com/>`_.
It's probably not very interesting to people looking for playing 2048, but may
be useful for people looking for learning Python (and some popular Python
packages, such as `PyQt`).
Written in Python 3.8 (and nothing more), the package is divided in 2 parts:
the backend and the frontend (or interface).

This package provides no concrete user interface for the game, but contains a
class that must be inherited by every actual frontend (more details below).


********
Features
********

* Customizable rules: you can configure the size of the game grid and the
  winning condition (wanna go beyond 2048?);
* Customizable looks: by subclassing the basic frontend and overriding its
  methods, you can make the game look any way you want, without touching the
  basic game logic;
* Automatic mode: you can replace human input with a function that picks a
  random direction! More useful for testing than actual gameplay, though.


**********
How to use
**********

Subclass `py2048.basefrontend.Base2048Frontend` and override the following
methods:

* `choose_direction`
* `player_quit`
* `player_victory`
* `player_loss`

`choose_direction` must return exactly one `py2048.Directions` object.
The other methods shouldn't return anything.
`player_quit` is called when the player exits the game before winning or
losing.


Wishlist
========

In the future, I'd like to create an AI to play the game!


Backend
=======

The backend is a pure-Python implementation of the original game logic;
it explains how equal numbers merge into their sum, "moving" from one tile into
another, and so on.
The main components are the `Cell` and the `Grid`.

The `Cell` class is a wrapper over an `int` that represents a tile in the game
grid.
It has a `locked` property, which is simply a `bool` that determines whether it
can change its stored `int`.
This prevents, for example, a 2 merging into a 2 and the resulting 4 merging
into another 4 all in a single game-turn.

The `Grid` is wrapper over a `dict` that maps points into `Cells`
(and points are named tuples that store x and y coordinates).
This class implements much of the game logic, such as determining how and when
one `Cell` can merge into another.


Frontend
========

The backend deals only with plain Python data, such as `int` and `dict`;
it is up to each frontend to actually collect user input and respond by
displaying the game data as a (hopefully) pretty interface.
Each frontend is a Python class that inherits from `Base2048Frontend`, the only
frontend-related implementation in this package.
This base class contains the main game loop that runs until a tile numbered
with the winning condition has formed or the player has no valid movements
available.

