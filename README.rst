######
py2048
######

.. image:: https://img.shields.io/github/license/dasld/py2048base?color=blue&style=flat-square   :alt: GitHub
.. image:: https://img.shields.io/pypi/v/py2048base?color=green&style=flat-square   :alt: PyPI

**py2048** is a clone of the famous game_ by `Gabriele Cirulli`__.
It's probably not very interesting to people looking for playing 2048, but may
be useful for people looking for learning Python.
It's written in pure Python 3.8 and makes an effort not to use third-party libraries.
For example, the game grid could be a numpy matrix, but I'd rather not break a butterfly
upon a wheel.
The game's been divided in two parts:
the backend, and the frontends (or interfaces).

The package in this repository provides no concrete user interface for the game,
but contains a class that must be inherited by every actual frontend.


********
Features
********

* Customizable rules
      You can configure the size of the game grid and the winning condition
      (wanna go beyond 2048?);
* Customizable looks
      By subclassing the basic frontend and overriding its
      methods, you can make the game look any way you want, without touching the
      basic game logic;
* Automatic mode
      You can replace human input with a function that picks a
      random direction! More useful for testing than actual gameplay, though.


**********
How to use
**********

To implement a frontend
=======================

The backend takes input (in the form of a `py2048.Directions` object),
processes it, and waits for the next input.
This loops until
the player exits, or
the player wins for the first time in this session, or
the player runs out of valid movements.
It's a pure-Python implementation of the original game logic:
it makes equal numbers merge into their sum, "moving" from one tile into
another, and so on.
The backend deals only with plain Python data, such as `int` and `dict`;
it is up to each frontend to actually collect the input and display the
updated game state as a (hopefully) pretty interface.

To write such frontend, subclass `py2048.basefrontend.Base2048Frontend`
and override the following methods:

* `choose_direction`
* `on_player_quit`
* `on_player_victory`
* `on_player_overvictory`
* `on_player_loss`

`choose_direction` must return exactly one `py2048.Directions` object.
If writing a graphical frontend (a GUI), you'll probably want to create a "worker"
thread that runs the backend's loop and waits for a condition when it reaches
the `choose_direction` call.
The main thread will then be responsible for storing user input somewhere accessible
by the worker thread and "waking it up".
The other overriden methods shouldn't return anything.
`player_quit` is called when the player exits the game before winning or
losing.
An "overvictory" is what happens when the grid "jams" (runs out of valid movements)
but the player had already won (had already reached the target goal number).

To run tests
============

We're using the `pytest` library to check the correctness of the basic
data structures.
To run the tests, open a terminal, move into the root folder of the project
(the one which contains `setup.py`), and type the following:

    pytest-3 -v py2048/test.py

Make sure you're in the right folder,
that there are no slashes in the command, and
that it doesn't end with *.py*.
Alternatively, use

    make test


********
Wishlist
********

In the future, I'd like to create an AI to play the game!


------------

************
How it works
************

Backend
=======

Its main components are the `Cell` and the `Grid`.
The `Cell` class is a wrapper over an `int` that represents a tile in the game
grid.
It has a `locked` property, which is simply a `bool` that determines whether it
can change its stored `int` in this cycle.
A cycle is what happens between the arrival of a valid user input and the moment
the game pauses to get the next input.
This `locked` property prevents a 2 merging into a 2 and the resulting 4 merging
into another 4 all in a single cycle, for example.
If you play the original game, you'll notice that is not allowed.

The `Grid` is a wrapper over a `dict` that maps points into `Cells`
(and points are named tuples that store x and y coordinates).
This class (along with `py2048.basefrontend.Base2048Frontend`), implements most
of the game logic.
It's responsible for determining how and when one `Cell` can merge into another,
updating the score, and so on.


Frontend
========




.. _game: https://play2048.co/
.. _cirulli: http://gabrielecirulli.com
__ cirulli_
