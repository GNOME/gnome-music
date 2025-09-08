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

    This works by keeping a local shuffle dictionary and shuffling
    the values as needed.

    This is meant for the Queue and as such a position in the
    playlist is required for the shuffling. The model shuffles the
    items after the given position. When deshuffling it will only
    deshuffle the items that are still left.
    """

    __gtype_name__ = "ShuffleListModel"

    def __init__(self, model: Gio.ListModel) -> None:
        """Initialize the list model

        :param Gio.ListModel model: Model to shuffle
        """
        super().__init__()

        self._log = MusicLogger()

        self._model = model
        self._model.connect("items-changed", self._on_items_changed)

        self._shuffle_dict: dict[int, int] = {}
        self._shuffled = False

    def _on_items_changed(
            self, model: Gio.ListModel, position: int, removed: int,
            added: int) -> None:
        if self._shuffled:
            self.shuffle(position)

    def do_get_item(self, position: int) -> CoreSong:
        if not self._shuffle_dict:
            return self._model.get_item(position)

        return self._model.get_item(self._shuffle_dict[position])

    def do_get_n_items(self):
        return self._model.get_n_items()

    def do_get_item_type(self):
        return self._model.get_item_type()

    def shuffle(self, position: int) -> None:
        """Shuffle the model

        :param int position: Shuffle the remaining items from this
            position on
        """
        self._shuffled = True
        n_items = self._model.get_n_items()
        if n_items == 0:
            return

        keys_list = list(range(0, position + 1))
        dict_before = dict(zip(keys_list, keys_list))

        positions_list = list(range(position + 1, n_items))
        dict_after = dict(
            zip(
                positions_list,
                sample(positions_list, len(positions_list))
            )
        )

        self._shuffle_dict = dict_before | dict_after
        self._log.debug(f"Shuffled dict: {self._shuffle_dict}")

    def deshuffle(self, position: int) -> None:
        """Deshuffle the model

        :param int position: Deshuffle the remaining items from this
            position on
        """

        self._shuffled = False

        n_items = self._model.get_n_items()
        if n_items == 0:
            return

        dict_before = {
            k: self._shuffle_dict[k]
            for k in list(self._shuffle_dict)[:position + 1]
        }

        dict_after = dict(
            zip(
                list(range(position + 1, n_items)),
                sorted(list(self._shuffle_dict.values())[position + 1:])
            )
        )

        self._shuffle_dict = dict_before | dict_after
        self._log.debug(f"Deshuffled dict: {self._shuffle_dict}")
