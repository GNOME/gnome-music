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

from gnomemusic.artistart import ArtistArt
import gnomemusic.utils as utils


class CoreArtist(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    artist = GObject.Property(type=str)
    media = GObject.Property(type=Grl.Media)

    def __init__(self, media, coremodel):
        super().__init__()

        self._cached_thumbnail_uri = None
        self._coremodel = coremodel
        self._model = None
        self._selected = False
        self._thumbnail = None

        self.update(media)

    def update(self, media):
        self.props.media = media
        self.props.artist = utils.get_artist_name(media)

    @GObject.Property(type=Gio.ListModel, default=None)
    def model(self):
        if self._model is None:
            self._model = self._coremodel.get_artist_album_model(
                self.props.media)
            self._model.connect("items-changed", self._on_items_changed)

        return self._model

    def _on_items_changed(self, model, pos, removed, added):
        with self.freeze_notify():
            for corealbum in self._model:
                corealbum.props.selected = self.props.selected

    @GObject.Property(type=bool, default=False)
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        if value == self._selected:
            return

        self._selected = value

        # The model is loaded on-demand, so the first time the model is
        # returned it can still be empty. This is problem for returning
        # a selection. Trigger loading of the model here if a selection
        # is requested, it will trigger the filled model update as
        # well.
        self.props.model.items_changed(0, 0, 0)

    @GObject.Property(type=str, default=None)
    def thumbnail(self):
        if self._thumbnail is None:
            self._thumbnail = ""
            ArtistArt(self, self._coremodel)

        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, value):
        self._thumbnail = value

    @GObject.Property(type=str, default=None)
    def cached_thumbnail_uri(self):
        return self._cached_thumbnail_uri

    @cached_thumbnail_uri.setter
    def cached_thumbnail_uri(self, value):
        self._cached_thumbnail_uri = value
