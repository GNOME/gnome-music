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
gi.require_versions({"Grl": "0.3"})
from gi.repository import Grl, Gtk, GObject

from gnomemusic.artistart import ArtistArt
from gnomemusic.corealbum import CoreAlbum
import gnomemusic.utils as utils


class CoreArtist(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    artist = GObject.Property(type=str)
    media = GObject.Property(type=Grl.Media)

    def __init__(self, application, media):
        """Initiate the CoreArtist object

        :param Application application: The application object
        :param Grl.Media media: A media object
        """
        super().__init__()

        self._application = application
        self._coregrilo = application.props.coregrilo
        self._coremodel = application.props.coremodel
        self._model = None
        self._thumbnail = None

        self.update(media)

    def update(self, media):
        self.props.media = media
        self.props.artist = utils.get_artist_name(media)

    def _get_artist_album_model(self):
        albums_model_filter = Gtk.FilterListModel.new(
            self._coremodel.props.albums)
        albums_model_filter.set_filter(Gtk.AnyFilter())

        albums_sort_exp = Gtk.PropertyExpression.new(CoreAlbum, None, "year")
        albums_sorter = Gtk.StringSorter.new(albums_sort_exp)
        albums_model_sort = Gtk.SortListModel.new(
            albums_model_filter, albums_sorter)

        self._coregrilo.get_artist_albums(
            self.props.media, albums_model_filter)

        return albums_model_sort

    @GObject.Property(type=Gtk.SortListModel, default=None)
    def model(self):
        if self._model is None:
            self._model = self._get_artist_album_model()

        return self._model

    @GObject.Property(type=str, default=None)
    def thumbnail(self):
        """Artist art thumbnail retrieval

        :return: The artist art uri or "generic"
        :rtype: string
        """
        if self._thumbnail is None:
            self._thumbnail = "generic"
            ArtistArt(self._application, self)

        return self._thumbnail

    @thumbnail.setter  # type: ignore
    def thumbnail(self, value):
        """Artist art thumbnail setter

        :param string value: uri or "generic"
        """
        self._thumbnail = value

        if self._thumbnail != "generic":
            self.props.media.set_thumbnail(self._thumbnail)
