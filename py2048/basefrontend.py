# -*- coding: utf-8 -*-
#
# basefrontend.py
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

"""Declares the Base2048Frontend class, which runs the game loop and
updates the game grid according to player input.
"""

import random
from abc import ABC, abstractmethod
from typing import Any, final, Optional

from py2048.core import Directions
from py2048.grid import Grid
from py2048.utils import Base2048Error, type_check


class Base2048Frontend(ABC):
    """Abstract class that implements the `play2048` method.

    A concrete frontend should inherit from this class, but shouldn't
    override this method.
    Many other methods are 'hooks' that either can, should, or must be
    overridden.
    """

    # a tuple version of the enum to make it work with `random`
    DIRECTIONS = tuple(Directions)
    # how many seconds to sleep when in auto mode
    SLEEP_S = 1
    # converting seconds to milliseconds
    SLEEP_MS = round(SLEEP_S * 1_000)

    def restart(self) -> None:
        self.victory = False
        self.grid.reset()
        self.grid.seed()

    def __init__(
        self,
        grid: Grid,
        is_random: bool,
        *,  # makes the remaining arguments keyword-only
        goal: Optional[int] = None,
    ) -> None:
        # first, perform some checks
        type_check(grid, Grid)
        # `goal = goal or 2048` would allow "goal = 0" to pass silently
        if goal is None:
            goal = 2048
        elif not grid.is2048like(goal):
            raise ValueError(
                "goal must be a positive power of 2 "
                f"smaller than {grid.CEILING}"
            )
        # checks passed
        self.grid = grid
        self.goal = goal
        if is_random:
            self.choice_function = self.guess_direction
        else:
            self.choice_function = self.choose_direction
        self.is_random = is_random
        self.victory = False

    # play hooks: don't need to be overridden, but probably should
    def on_play(self) -> Any:
        pass

    def on_attempt(self) -> Any:
        pass

    def after_choice(self, choice: Directions) -> Any:
        pass

    def after_change(self, choice: Directions) -> Any:
        pass

    def after_nochange(self, choice: Directions) -> Any:
        pass

    def after_attempt(self, choice: Directions) -> Any:
        pass

    def after_play(self) -> Any:
        pass

    def guess_direction(self) -> Directions:
        return random.choice(self.DIRECTIONS)

    # MAIN LOOP: shouldn't be overridden
    @final
    def play2048(self) -> None:
        """Main loop that repeatedly calls `self.choice_function` until
        either a) the grid is jammed; or b) the player exits; or c) the
        goal has been reached for the first time.

        The player can exit in two ways:
        1) If `self.choice_function` raises `KeyboardInterrupt`, the
        loop returns immediately, skipping `self.after_play()`.
        2) If it raises `EOFError`, the loop ends and then calls
        `self.after_play`.

        This method is not supposed to be overridden when subclassing
        this class.
        """

        grid = self.grid
        # calling `on_play` before checks allows this method to ensure
        # the grid's ready to enter the game loop
        self.on_play()
        # will become True iff the loop ended not due to a grid jamming
        player_quit = False
        if grid.is_empty:
            raise Base2048Error(
                f"Asked to play 2048 with an empty grid:\n{grid}"
            )
        # the actual loop
        is_jammed = grid.is_jammed
        if is_jammed:
            raise Base2048Error(
                f"Asked to play 2048 with a jammed grid:\n{grid}"
            )
        while not is_jammed:
            self.on_attempt()
            try:
                choice = self.choice_function()
            except KeyboardInterrupt:
                # quickly exit due to Ctrl-C
                print(flush=True)  # makes terminal looks nicer
                return
            except EOFError:
                # Ctrl-D/Z or some quit-command
                player_quit = True
                break
            assert choice in Directions, (
                f"grid.Grid.choice_function returned {choice!r}; "
                "had to be a Directions instance"
            )
            self.after_choice(choice)
            dragged = grid.drag(choice)
            # we don't need to update is_jammed if the game state
            # didn't change!
            if dragged:
                self.after_change(choice)
                is_jammed = grid.is_jammed
            else:
                self.after_nochange(choice)
            self.after_attempt(choice)
            # if the player kept playing after winning, we don't want
            # to exit this loop
            if not self.victory and grid.largest >= self.goal:
                # first victory in this game loop; if the player keeps
                # playing, the time the grid jams will be considered an
                # "overvictory" instead of a loss
                self.victory = True
                break
        # after loop stuff
        self.after_play()
        if player_quit:
            self.on_player_quit()
        elif self.victory:
            if is_jammed:
                # the game has jammed, but the player had already won,
                # so it's an "overvictory"
                self.on_player_overvictory()
            else:
                # player's winning for the first time
                self.on_player_victory()
        else:
            assert is_jammed, (
                "If the player neither won nor quit and the grid isn't "
                "jammed, why did the game loop stop?"
            )
            self.on_player_loss()

    # the following methods MUST be overridden
    @abstractmethod
    def choose_direction(self) -> Directions:
        pass

    @abstractmethod
    def on_player_quit(self) -> Any:
        pass

    @abstractmethod
    def on_player_victory(self) -> Any:
        pass

    @abstractmethod
    def on_player_overvictory(self) -> Any:
        pass

    @abstractmethod
    def on_player_loss(self) -> Any:
        pass
