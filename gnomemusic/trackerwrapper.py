# Copyright 2019 The GNOME Music developers
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

from enum import IntEnum

from gi.repository import Gio, GLib, GObject, Tracker


class TrackerState(IntEnum):
    """Tracker Status
    """
    AVAILABLE = 0
    UNAVAILABLE = 1
    OUTDATED = 2


class TrackerWrapper(GObject.GObject):

    def __init__(self, application):
        """Create a connection to an instance of Tracker

        :param Application application: The application object
        """
        super().__init__()

        self._log = application.props.log

        self._tracker = None
        self._tracker_available = TrackerState.UNAVAILABLE

        try:
            self._tracker = Tracker.SparqlConnection.new(
                Tracker.SparqlConnectionFlags.NONE,
                Gio.File.new_for_path(self.cache_directory()),
                Tracker.sparql_get_ontology_nepomuk(),
                None)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self.notify("tracker-available")
            return

        query = """
        SELECT
            ?e
        {
            GRAPH tracker:Audio {
                ?e a tracker:ExternalReference .
            }
        }""".replace("\n", "").strip()

        self._tracker.query_async(query, None, self._query_version_check)

    def _query_version_check(self, klass, result):
        try:
            klass.query_finish(result)
            self._tracker_available = TrackerState.AVAILABLE
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._tracker_available = TrackerState.OUTDATED

        self.notify("tracker-available")

    def cache_directory(self):
        """Get directory which contains Music private data.

        :returns: private store path
        :rtype: str
        """
        return GLib.build_pathv(
            GLib.DIR_SEPARATOR_S,
            [GLib.get_user_cache_dir(), "gnome-music", "db"])

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def tracker(self):
        return self._tracker

    @GObject.Property(
        type=int, default=TrackerState.UNAVAILABLE,
        flags=GObject.ParamFlags.READABLE)
    def tracker_available(self):
        """Get Tracker availability.

        Tracker is available if a SparqlConnection has been opened and
        if a query can be performed.

        :returns: tracker availability
        :rtype: TrackerState
        """
        return self._tracker_available

    def location_filter(self):
        try:
            music_dir = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
            assert music_dir is not None
        except (TypeError, AssertionError):
            self._log.message("XDG Music dir is not set")
            return None

        music_dir = Tracker.sparql_escape_string(
            GLib.filename_to_uri(music_dir))

        query = "FILTER (STRSTARTS(nie:isStoredAs(?song), '{}/'))".format(
            music_dir)

        return query

    def _update_favorite(self, media):
        """Update favorite state of a song

        :param Grl.Media media: media which contains updated favorite state
        """
        if (media.get_favourite()):
            update = """
            INSERT DATA {
                <%(urn)s> a nmm:MusicPiece ;
                          nao:hasTag nao:predefined-tag-favorite .
            }
            """.replace("\n", "").strip() % {
                "urn": media.get_id(),
            }
        else:
            update = """
            DELETE DATA {
                <%(urn)s> nao:hasTag nao:predefined-tag-favorite .
            }
            """.replace("\n", "").strip() % {
                "urn": media.get_id(),
            }

        def _update_favorite_cb(conn, res):
            try:
                conn.update_finish(res)
            except GLib.Error as e:
                self._log.warning("Unable to update favorite: {}".format(
                    e.message))

        self._tracker.update_async(update, None, _update_favorite_cb)

    def _update_play_count(self, media):
        update = """
        DELETE WHERE {
            <%(urn)s> nie:usageCounter ?count .
        };
        INSERT DATA {
            <%(urn)s> a nmm:MusicPiece ;
                      nie:usageCounter %(count)d .
        }
        """.replace("\n", "").strip() % {
            "urn": media.get_id(),
            "count": media.get_play_count(),
        }

        def _update_play_count_cb(conn, res):
            try:
                conn.update_finish(res)
            except GLib.Error as e:
                self._log.warning("Unable to update play count: {}".format(
                    e.message))

        self._tracker.update_async(update, None, _update_play_count_cb)

    def _update_last_played(self, media):
        last_played = media.get_last_played().format_iso8601()
        update = """
        DELETE WHERE {
            <%(urn)s> nie:contentAccessed ?accessed
        };
        INSERT DATA {
            <%(urn)s> a nmm:MusicPiece ;
                      nie:contentAccessed "%(last_played)s"
        }
        """.replace("\n", "").strip() % {
            "urn": media.get_id(),
            "last_played": last_played,
        }

        def _update_last_played_cb(conn, res):
            try:
                conn.update_finish(res)
            except GLib.Error as e:
                self._log.warning("Unable to update play count: {}".format(
                    e.message))

        self._tracker.update_async(update, None, _update_last_played_cb)

    def update_tag(self, media, tag):
        """Update property of a resource.

        :param Grl.Media media: media which contains updated tag
        :param str tag: tag to update
        """
        if tag == "favorite":
            self._update_favorite(media)
        elif tag == "last-played":
            self._update_last_played(media)
        elif tag == "play-count":
            self._update_play_count(media)
        else:
            self._log.warning("Unknown tag: '{}'".format(tag))
