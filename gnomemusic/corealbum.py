# Copyright 2019 The GNOME Music developers
#
# GNOME Music is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# GNOME Music is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with GNOME Music; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# The GNOME Music authors hereby grant permission for non-GPL compatible
# GStreamer plugins to be used and distributed together with GStreamer
# and GNOME Music.  This permission is above and beyond the permissions
# granted by the GPL license by which GNOME Music is covered.  If you
# modify this code, you may extend this exception to your version of the
# code, but you are not obligated to do so.  If you do not wish to do so,
# delete this exception statement from your version.

import gi
gi.require_version('Grl', '0.3')
from gi.repository import Gio, Grl, GObject

from gnomemusic import log
import gnomemusic.utils as utils


class CoreAlbum(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    artist = GObject.Property(type=str)
    composer = GObject.Property(type=str, default=None)
    duration = GObject.Property(type=int, default=0)
    media = GObject.Property(type=Grl.Media)
    title = GObject.Property(type=str)
    year = GObject.Property(type=str, default="----")

    @log
    def __init__(self, media, coremodel):
        super().__init__()

        self._coremodel = coremodel
        self._model = None
        self._selected = False
        self.update(media)

    @log
    def update(self, media):
        self.props.media = media
        self.props.artist = utils.get_artist_name(media)
        self.props.composer = media.get_composer()
        self.props.title = utils.get_media_title(media)
        self.props.year = utils.get_media_year(media)

    @GObject.Property(
        type=Gio.ListModel, default=None, flags=GObject.ParamFlags.READABLE)
    def model(self):
        if self._model is None:
            self._model = self._coremodel.get_album_model(self.props.media)
            self._model.connect("items-changed", self._on_list_items_changed)

        self._on_list_items_changed(self._model, None, None, None)

        return self._model

    def _on_list_items_changed(self, model, pos, removed, added):
        with self.freeze_notify():
            for coredisc in model:
                coredisc.connect("notify::duration", self._on_duration_changed)
                coredisc.props.selected = self.props.selected

    def _on_duration_changed(self, coredisc, duration):
        duration = 0

        for coredisc in self.props.model:
            duration += coredisc.props.duration

        self.props.duration = duration

    @GObject.Property(type=bool, default=False)
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value

        # The model is loaded on-demand, so the first time the model is
        # returned it can still be empty. This is problem for returning
        # a selection. Trigger loading of the model here if a selection
        # is requested, it will trigger the filled model update as
        # well.
        self.props.model
