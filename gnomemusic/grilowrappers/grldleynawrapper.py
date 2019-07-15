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
from gi.repository import Grl, GObject

from gnomemusic.coreartist import CoreArtist


class GrlDLeynaWrapper(GObject.GObject):

    METADATA_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_ARTIST,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_CREATION_DATE,
        Grl.METADATA_KEY_COMPOSER,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_FAVOURITE,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_LYRICS,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_THUMBNAIL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    def __repr__(self):
        return "<GrlDLeynaWrapper>"

    def __init__(self, source, coremodel, core_selection, grilo):
        super().__init__()

        self._coremodel = coremodel
        self._core_selection = core_selection
        self._grilo = grilo
        self._source = source
        self._model = self._coremodel.props.songs
        self._albums_model = self._coremodel.props.albums
        self._album_ids = {}
        self._artists_model = self._coremodel.props.artists

        Grl.init(None)

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._full_options = Grl.OperationOptions()
        self._full_options.set_resolution_flags(
            Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY)

        # self._initial_fill(self._source)
        # self._initial_albums_fill(self._source)
        self._initial_artists_fill(self._source)

        # self._source.connect("content-changed", self._on_content_changed)

    @GObject.Property(
        type=Grl.Source, default=None, flags=GObject.ParamFlags.READABLE)
    def source(self):
        return self._source

    def _initial_artists_fill(self, source):
        query = """
        upnp:class derivedfrom 'object.container.person.musicArtist'
        """.replace('\n', ' ').strip()

        options = self._fast_options.copy()

        source.query(
            query, self.METADATA_KEYS, options, self._add_to_artists_model)

    def _add_to_artists_model(self, source, op_id, media, user_data, error):
        if error:
            print("ERROR", error)
            return

        if not media:
            print("NO MEDIA", source, op_id, media, error)
            return

        artist = CoreArtist(media, self._coremodel, self._grilo)
        artist.props.artist = media.get_title() + " (upnp)"
        self._artists_model.append(artist)
        print(
            "ADDING DLNA ARTIST", media.get_title(), media.get_artist(),
            media.get_id())

    def get_artist_albums(self, artist, filter_model):
        pass

    def populate_album_disc_songs(self, media, discnr, callback):
        pass

    def search(self, text):
        pass
