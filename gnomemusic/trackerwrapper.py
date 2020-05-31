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

import os

from enum import Enum, IntEnum

from gi.repository import Gio, GLib, GObject, Tracker

from gnomemusic.musiclogger import MusicLogger


class TrackerState(IntEnum):
    """Tracker Status
    """
    AVAILABLE = 0
    UNAVAILABLE = 1
    OUTDATED = 2


class MbReference(Enum):
    """Enum to deal with musicbrainz references updates."""
    RECORDING = ("Recording", "song", "get_mb_recording_id")
    TRACK = ("Track", "song", "get_mb_track_id")
    ARTIST = ("Artist", "performer", "get_mb_artist_id")
    RELEASE = ("Release", "album", "get_mb_release_id")
    RELEASE_GROUP = ("Release_Group", "album", "get_mb_release_group_id")

    def __init__(self, source, owner, method):
        """Intialize source, owner and method"""
        self.source = "https://musicbrainz.org/doc/{}".format(source)
        self.owner = owner
        self.method = method


class TrackerWrapper(GObject.GObject):
    """Create a connection to an instance of Tracker"""

    def __init__(self):
        super().__init__()

        self._log = MusicLogger()

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
        return os.path.join(GLib.get_user_cache_dir(), 'gnome-music', 'db')

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

        query = "FILTER (STRSTARTS(nie:isStoredAs(?song), '{}/'))".format(music_dir)

        return query

    def _resource_added(self, conn, res, data):
        try:
            conn.update_finish(res)
        except GLib.Error as e:
            self._log.warning(
                "Unable to associate resource: {}".format(e.message))

        media, data, callback = data
        if callback:
            callback(media, data)

    def _add_resource_to_piece(self, conn, res, data):
        media, urn, rdf_property, owner, tags, callback = data
        if conn is not None:
            try:
                conn.update_finish(res)
            except GLib.Error as e:
                self._log.warning(
                    "Unable to create new resource: {}".format(e.message))
                if callback:
                    callback(media, tags)
                return

        where_owner = {
            "album": "nmm:musicAlbum ?album ;",
            "albumdisc": "nmm:musicAlbumDisc ?albumdisc ;",
            "performer": "nmm:performer ?performer ;",
            "song": ""
        }

        query_insert_resource = """
        INSERT {
            ?%(owner)s %(property)s <%(urn)s> }
        WHERE {
            ?song a nmm:MusicPiece ;
                    %(where_owner)s
                    nie:url "%(url)s" .
        }
        """.replace("\n", "").strip() % {
            "owner": owner,
            "property": rdf_property,
            "urn": urn,
            "where_owner": where_owner[owner],
            "url": media.get_url()
        }

        self._tracker.update_async(
            query_insert_resource, GLib.PRIORITY_LOW, None,
            self._resource_added, [media, tags, callback])

    def _create_new_external_reference(self, conn, res, data):
        media, mbref, tags = data
        try:
            conn.update_finish(res)
        except GLib.Error as e:
            self._log.warning(
                "Unable to delete previous external reference: {}".format(
                    e.message))
            self.update_tags(tags)
            return

        def _reference_exists_cb(conn, res, data):
            try:
                cursor = conn.query_finish(res)
            except GLib.Error as e:
                self._log.warning(
                    "Unable to check external if reference exists: {}".format(
                        e.message))
                self.update_tags(tags)
                return

            data = [
                media, "", "tracker:hasExternalReference", mbref.owner, tags,
                self.update_tags]

            if cursor.next():
                data[1] = cursor.get_string(0)[0]
                self._add_resource_to_piece(None, None, data)
                return

            # In Tracker 3.0, Musicbrainz resources urns have changed
            # See
            # https://gitlab.gnome.org/GNOME/tracker-miners/merge_requests/126
            mb_id = getattr(media, mbref.method)()
            mb_source = mbref.source
            source_escaped = Tracker.sparql_escape_uri(mb_source)
            new_urn = "urn:ExternalReference:{}:{}".format(
                source_escaped, mb_id)

            query_new_reference = """
            INSERT DATA {
                <%(urn)s> a tracker:ExternalReference ;
                            tracker:referenceSource "%(mb_source)s" ;
                            tracker:referenceIdentifier "%(mb_id)s" .
            }
            """.replace("\n", "").strip() % {
                "urn": new_urn,
                "mb_source": mb_source,
                "mb_id": mb_id
            }

            data[1] = new_urn
            self._tracker.update_async(
                query_new_reference, GLib.PRIORITY_LOW, None,
                self._add_resource_to_piece, data)

        mb_id = getattr(media, mbref.method)()
        query_reference_exists = """
        SELECT
            ?reference
        WHERE{
            ?reference a tracker:ExternalReference ;
                         tracker:referenceIdentifier "%(mb_id)s"
        }
        """.replace("\n", "").strip() % {
            "mb_id": mb_id
        }

        self._tracker.query_async(
            query_reference_exists, None, _reference_exists_cb, None)

    def _update_reference(self, media, mbref, tags):
        query_delete = """
        DELETE {
            ?%(owner)s tracker:hasExternalReference ?t
        }
        WHERE {
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album ;
                    nmm:performer ?performer ;
                    nie:url "%(url)s" .
            ?%(owner)s tracker:hasExternalReference ?t .
            ?t tracker:referenceSource "%(mb_source)s"
        }
        """.replace("\n", "").strip() % {
            "owner": mbref.owner,
            "url": media.get_url(),
            "mb_source": mbref.source
        }

        data = [media, mbref, tags]
        self._tracker.update_async(
            query_delete, GLib.PRIORITY_LOW, None,
            self._create_new_external_reference, data)

    def _create_new_artist(self, conn, res, data):
        media, owner, tags = data
        try:
            conn.update_finish(res)
        except GLib.Error as e:
            self._log.warning("Unable to delete previous artist: {}".format(
                e.message))
            self.update_tags(media, tags)
            return

        def _artist_exists_cb(conn, res, ex_data):
            try:
                cursor = conn.query_finish(res)
            except GLib.Error:
                self.update_tags(media, tags)
                return

            data = [media, "", "nmm:performer", owner, tags, self.update_tags]
            if owner == "album":
                data[2] = "nmm:albumArtist"

            if cursor.next():
                data[1] = cursor.get_string(0)[0]
                self._add_resource_to_piece(None, None, data)
                return

            escaped_urn = Tracker.sparql_escape_uri(artist_name)
            new_urn = "urn:artist:{}".format(escaped_urn)
            data[1] = new_urn

            query_new_artist = """
            INSERT DATA {
                <%(urn)s> a nmm:Artist ;
                            nmm:artistName "%(name)s" .
            }
            """.replace("\n", "").strip() % {
                "urn": new_urn,
                "name": escaped_name
            }

            self._tracker.update_async(
                query_new_artist, GLib.PRIORITY_LOW, None,
                self._add_resource_to_piece, data)

        if owner == "album":
            artist_name = media.get_album_artist()
        else:
            artist_name = media.get_artist()

        escaped_name = Tracker.sparql_escape_string(artist_name)
        query_artist_exists = """
        SELECT
            ?artist
        WHERE{
            ?artist a nmm:Artist ;
                      nmm:artistName "%(name)s" .
        }
        """.replace("\n", "").strip() % {
            "name": escaped_name
        }

        self._tracker.query_async(
            query_artist_exists, None, _artist_exists_cb, None)

    def _update_artist(self, media, tags):
        query_delete = """
        DELETE {
            ?song nmm:performer ?artist
        }
        WHERE {
            ?song a nmm:MusicPiece ;
                    nmm:performer ?artist ;
                    nie:url "%(url)s" .
        }
        """.replace("\n", "").strip() % {
            "url": media.get_url()
        }

        self._tracker.update_async(
            query_delete, GLib.PRIORITY_LOW, None, self._create_new_artist,
            [media, "song", tags])

    def _get_album_urn_suffix(self, media):
        shared = ""
        if media.get_album_artist():
            shared += ":{}".format(media.get_album_artist())
        if media.get_creation_date():
            creation_date = media.get_creation_date()
            date_str = creation_date.format("%FT%TZ")
            shared += ":{}".format(date_str)

        suffix = "{}{}".format(media.get_album(), shared)
        return Tracker.sparql_escape_uri(suffix)

    def _album_disc_created(self, conn, res, data):
        media, album_disc_urn, tags = data
        try:
            conn.update_finish(res)
        except GLib.Error as e:
            self._log.warning(
                "Unable to create new album disc: {}".format(e.message))
            self.update_tags(media, tags)
            return

        def _album_get_cb(conn, res, cb_data):
            try:
                cursor = conn.query_finish(res)
            except GLib.Error as e:
                self._log.warning("Unable to get album: {}".format(e.message))
                self.update_tags(media, tags)
                return

            cursor.next()
            album_urn = cursor.get_string(0)[0]

            # add album disc to song
            data = [
                media, album_disc_urn, "nmm:musicAlbumDisc", "song", tags,
                None]
            self._add_resource_to_piece(None, None, data)

            # add album to album disc
            data = [
                media, album_urn, "nmm:albumDiscAlbum", "albumdisc", tags,
                self.update_tags]
            self._add_resource_to_piece(None, None, data)

        query_get_album = """
        SELECT
            ?album
        WHERE {
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album ;
                    nie:url "%(url)s" .
        }
        """.replace("\n", "").strip() % {
            "url": media.get_url()
        }
        self._tracker.query_async(
            query_get_album, None, _album_get_cb, None)

    def _create_new_album_disc(self, media, tags):
        def _album_disc_exists_cb(conn, res, ex_data):
            try:
                cursor = conn.query_finish(res)
            except GLib.Error as e:
                self._log.warning(
                    "Unable to check that album disc exists: {}".format(
                        e.message))
                self.update_tags(media, tags)
                return

            # If the album disc already exists, it means that the link
            # between the album disc and the album exists too. So, the
            # album disc just needs to be associated with the song.
            # If the album disc does not exist, it needs to be created.
            # Then, it needs to be associated with the song and the
            # nmm:albumDiscAlbum property of the album disc must be
            # created.
            if cursor.next():
                urn = cursor.get_string(0)[0]
                data = [
                    media, urn, "nmm:musicAlbumDisc", "song", tags,
                    self.update_tags]
                self._add_resource_to_piece(None, None, data)
                return

            disc_nr = media.get_album_disc_number()
            urn_suffix = self._get_album_urn_suffix(media)
            new_urn = "urn:album-disc:{}:Disc{}".format(urn_suffix, disc_nr)

            query_new_album_disc = """
            INSERT DATA {
                <%(urn)s> a nmm:MusicAlbumDisc ;
                            nmm:setNumber "%(disc_nr)s" .
            }
            """.replace("\n", "").strip() % {
                "urn": new_urn,
                "disc_nr": disc_nr
            }

            data = [media, new_urn, tags]
            self._tracker.update_async(
                query_new_album_disc, GLib.PRIORITY_LOW, None,
                self._album_disc_created, data)

        escaped_name = Tracker.sparql_escape_string(media.get_album())
        if media.get_album_artist():
            artist = Tracker.sparql_escape_uri(media.get_album_artist())
            artist_urn = 'urn:artist:{}'.format(artist)
            artist_cond = "nmm:albumDiscAlbum/nmm:albumArtist '{}' ;".format(
                artist_urn)
        else:
            artist_cond = ""

        query_album_disc_exists = """
        SELECT
            ?albumdisc
        WHERE {
            ?albumdisc a nmm:MusicAlbumDisc ;
                         nmm:setNumber %(disc_number)s ;
                         %(artist_cond)s
                         nmm:albumDiscAlbum/nie:title "%(title)s" .
        }
        """.replace("\n", "").strip() % {
            "disc_number": media.get_album_disc_number(),
            "artist_cond": artist_cond,
            "title": escaped_name
        }

        self._tracker.query_async(
            query_album_disc_exists, None, _album_disc_exists_cb, None)

    def _create_new_album(self, conn, res, data):
        media, tags = data
        try:
            conn.update_finish(res)
        except GLib.Error as e:
            self._log.warning(
                "Unable to delete previous album: {}".format(e.message))
            self.update_tags(media, tags)
            return

        def _album_exists_cb(conn, res, ex_data):
            try:
                cursor = conn.query_finish(res)
            except GLib.Error as e:
                self._log.warning(
                    "Unable to check that album exists: {}".format(e.message))
                self.update_tags(media, tags)
                return

            data = [
                media, "", "nmm:musicAlbum", "song", tags,
                self._create_new_album_disc]

            if cursor.next():
                data[1] = cursor.get_string(0)[0]
                self._add_resource_to_piece(None, None, data)
                return

            urn_suffix = self._get_album_urn_suffix(media)
            new_urn = "urn:album:{}".format(urn_suffix)
            album_title = Tracker.sparql_escape_string(media.get_album())

            query_new_album = """
            INSERT DATA {
                <%(urn)s> a nmm:MusicAlbum ;
                            nie:title "%(name)s" .
            }
            """.replace("\n", "").strip() % {
                "urn": new_urn,
                "name": album_title
            }

            data[1] = new_urn
            self._tracker.update_async(
                query_new_album, GLib.PRIORITY_LOW, None,
                self._add_resource_to_piece, data)

        album_title = Tracker.sparql_escape_string(media.get_album())
        if media.get_album_artist():
            artist = Tracker.sparql_escape_uri(media.get_album_artist())
            artist_urn = 'urn:artist:{}'.format(artist)
            artist_cond = "nmm:albumArtist '{}' ;".format(artist_urn)
        else:
            artist_cond = ""

        query_album_exists = """
        SELECT
            ?album
        WHERE {
            ?album a nmm:MusicAlbum ;
                     %(artist_cond)s
                     nie:title "%(title)s" .
        }
        """.replace("\n", "").strip() % {
            "artist_cond": artist_cond,
            "title": album_title
        }

        self._tracker.query_async(
            query_album_exists, None, _album_exists_cb, None)

    def _update_album(self, media, tags):
        query_delete = """
        DELETE {
            ?song nmm:musicAlbum ?album .
            ?song nmm:musicAlbumDisc ?album_disc .
        }
        WHERE {
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album ;
                    nmm:musicAlbumDisc ?album_disc ;
                    nie:url "%(url)s" .

        }
        """.replace("\n", "").strip() % {
            "url": media.get_url()
        }

        self._tracker.update_async(
            query_delete, GLib.PRIORITY_LOW, None, self._create_new_album,
            [media, tags])

    def _update_album_artist(self, media, tags):
        query_delete = """
        DELETE {
            ?album nmm:albumArtist ?artist
        }
        WHERE {
            ?album a nmm:MusicAlbum ;
                     nmm:albumArtist ?artist .
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album ;
                    nie:url "%(url)s" .
        }
        """.replace("\n", "").strip() % {
            "url": media.get_url()
        }

        self._tracker.update_async(
            query_delete, GLib.PRIORITY_LOW, None, self._create_new_artist,
            [media, "album", tags])

    def update_tags(self, media, tags):
        """Recursively update all tags.

        Update properties of a resource, for example, the title
        of an album.
        An album (MusicAlbum) is a resource associated with a
        MusicPiece via the `nmm:musicAlbum` property. So, when the
        album title of a song needs to be updated, then `nmm:musicAlbum`
        property needs to be removed. Then a new MusicAlbum needs to
        be created the new album (if it does not exist yet) and finally
        a new `nmm:musicAlbum` property needs to be set between the
        MusicPiece and the new MusicAlbum.

        For each tag, the following logic needs to be followed:
        1. Delete the link with previous tracker resource
        2. Create a new resource if it does not exist
        3. Associate the resource with the song, artist or album

        Tags are updated one after the other until the tags list
        is empty.

        :param Grl.Media media: media which contains updated tags
        :param deque tags: List of modified tags
        """
        try:
            tag = tags.popleft()
        except IndexError:
            self._log.debug("All tags have been updated.")
            return

        if tag == "album":
            self._update_album(media, tags)
        elif tag == "album-artist":
            self._update_album_artist(media, tags)
        elif tag == "artist":
            self._update_artist(media, tags)
        elif tag == "mb-recording-id":
            self._update_reference(media, MbReference.RECORDING, tags)
        elif tag == "mb-track-id":
            self._update_reference(media, MbReference.TRACK, tags)
        elif tag == "mb-artist-id":
            self._update_reference(media, MbReference.ARTIST, tags)
        elif tag == "mb-release-id":
            self._update_reference(media, MbReference.RELEASE, tags)
        elif tag == "mb-release-group-id":
            self._update_reference(media, MbReference.RELEASE_GROUP, tags)
        else:
            self._log.warning("Unknown tag: '{}'".format(tag))
            self.update_tags(media, tags)
