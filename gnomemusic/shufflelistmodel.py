# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from random import sample
import typing

from gi.repository import Gio, GObject

from gnomemusic.musiclogger import MusicLogger

if typing.TYPE_CHECKING:
    from gnomemusic.coresong import CoreSong


class ShuffleListModel(GObject.GObject, Gio.ListModel):
    """Shuffles the underlying list model

    This works by keeping a local shuffle list and shuffling the
    values as needed.

    This is meant for the Queue and as such a position in the
    playlist is required for the shuffling. The model shuffles the
    items after the given position. When deshuffling it will only
    deshuffle the items that are still left in the queue.
    """

    __gtype_name__ = "ShuffleListModel"

    shuffled = GObject.Property(type=bool, default=False)

    def __init__(self, model: Gio.ListModel) -> None:
        """Initialize the list model

        :param Gio.ListModel model: Model to shuffle
        """
        super().__init__()

        self._log = MusicLogger()

        self._model = model
        self._model.connect("items-changed", self._on_items_changed)

        self._shuffle_values: list[int] = []

    def _on_items_changed(
            self, model: Gio.ListModel, position: int, removed: int,
            added: int) -> None:
        # FIXME: Deal with item changes during play
        n_items = model.get_n_items()
        self._shuffle_values = list(range(0, n_items))

    def do_get_item(self, position: int) -> CoreSong:
        return self._model.get_item(self._shuffle_values[position])

    def do_get_n_items(self):
        return self._model.get_n_items()

    def do_get_item_type(self):
        return self._model.get_item_type()

    def shuffle(
            self, position: int, initial_song_position: int = 0) -> None:
        """Shuffle the model

        :param int position: Shuffle the remaining items from this
            position on
        :param int initial_song_position: The song index where to
            start shuffling from
        """
        self.props.shuffled = True
        if self._model.get_n_items() == 0:
            return

        list_before = list(self._shuffle_values[:position + 1])
        values_after = self._shuffle_values[position + 1:]
        list_after = sample(values_after, len(values_after))
        self._shuffle_values = list_before + list_after

        self._shuffle_values.remove(initial_song_position)
        self._shuffle_values = [initial_song_position] + self._shuffle_values

        self._log.debug(f"Shuffled order: {self._shuffle_values}")

    def deshuffle(self, position: int | None = None) -> None:
        """Deshuffle the model

        :param int position: Deshuffle the remaining items from this
            position on
        """
        self.props.shuffled = False

        if position is not None:
            list_before = list(self._shuffle_values[:position])
            list_position = list(self._shuffle_values[position:position + 1])
            list_after = sorted(self._shuffle_values[position + 1:])
            self._shuffle_values = list_before + list_position + list_after
        else:
            self._shuffle_values = sorted(self._shuffle_values)

        self._log.debug(f"Deshuffled order: {self._shuffle_values}")
