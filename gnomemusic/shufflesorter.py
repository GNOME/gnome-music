# Copyright 2023 The GNOME Music developers

from __future__ import annotations
from random import choice
from typing import Optional
import typing

from gi.repository import Gtk

if typing.TYPE_CHECKING:
    from gnomemusic.coresong import CoreSong

class ShuffleSorter(Gtk.Sorter):
    """Naive shuffler
    """

    def __init__(self) -> None:
        """
        """
        super().__init__()

        self._first_song: Optional[None] = None

    def first_song(self, coresong: Optional[CoreSong]) -> None:
        self._first_song = coresong

    def do_compare(
            self, coresong_a: CoreSong, coresong_b: CoreSong) -> Gtk.Ordering:
        s = [Gtk.Ordering.SMALLER, Gtk.Ordering.EQUAL, Gtk.Ordering.LARGER]
        if self._first_song is None:
            return choice(s)
        elif self._first_song == coresong_a:
            return Gtk.Ordering.SMALLER
        elif self._first_song == coresong_b:
            return Gtk.Ordering.LARGER

        return choice(s)
