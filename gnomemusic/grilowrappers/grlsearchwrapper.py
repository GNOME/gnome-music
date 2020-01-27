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
from gi.repository import Gfm, Gio, Grl, GObject

from gnomemusic.coresong import CoreSong


class GrlSearchWrapper(GObject.GObject):
    """Wrapper for a generic Grilo source search.

    Grilo has -besides source specific queries- an option to do a
    generic source search, if the source supports it. This class wraps
    such a search.
    """

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
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_THUMBNAIL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    def __init__(self, source, coremodel, application, grilo):
        """Initialize a search wrapper

        Initialize a generic Grilo source search wrapper.

        :param Grl.Source source: The Grilo source to wrap
        :param CoreModel coremodel: CoreModel instance to use models
         from
        :param Application application: Application instance
        :param CoreGrilo grilo: The CoreGrilo instance
        """
        super().__init__()

        self._coremodel = coremodel
        self._coreselection = application.props.coreselection
        self._grilo = grilo
        self._source = source

        self._song_search_proxy = self._coremodel.props.songs_search_proxy

        self._song_search_store = Gio.ListStore.new(CoreSong)
        # FIXME: Workaround for adding the right list type to the proxy
        # list model.
        self._song_search_model = Gfm.FilterListModel.new(
            self._song_search_store)
        self._song_search_model.set_filter_func(lambda a: True)
        self._song_search_proxy.append(self._song_search_model)

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_count(25)
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

    def search(self, text):
        """Initiate a search

        :param str text: The text to search
        """
        with self._song_search_store.freeze_notify():
            self._song_search_store.remove_all()

        def _search_result_cb(source, op_id, media, remaining, error):
            if error:
                print("error")
                return
            if media is None:
                return

            coresong = CoreSong(media, self._coreselection, self._grilo)
            coresong.props.title = (
                coresong.props.title + " (" + source.props.source_name + ")")

            self._song_search_store.append(coresong)

        self._source.search(
            text, self.METADATA_KEYS, self._fast_options, _search_result_cb)
