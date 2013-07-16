/*
* Copyright (c) 2013 Igalia S.L.
* Authored by: Juan A. Suarez Romero <jasuarez@igalia.com>
* Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
* Copyright (c) 2013 Sai Suman Prayaga
* Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
*
* Gnome Music is free software; you can Public License as published by the
* Free Software Foundation; either version 2 of the License, or (at your
* option) any later version.
*
* The Gnome Music authors hereby grant permission for non-GPL compatible
* GStreamer plugins to be used and distributed together with GStreamer and
* Gnome Music. This permission is above and beyond the permissions granted by
* the GPL license by which Gnome Music is covered. If you modify this code, you may 
* extend this exception to your version of the code, but you are not obligated 
* to do so. If you do not wish to do so, delete this exception statement from 
* your version.
*
* Gnome Music is distributed in the hope that it will be useful, but
* WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
* or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
* for more details.
*
* You should have received a copy of the GNU General Public License along
* with Gnome Music; if not, write to the Free Software Foundation,
* Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
*
*/

const Tracker = imports.gi.Tracker;

const album = 'SELECT DISTINCT rdf:type(?album) tracker:id(?album) as id (SELECT nmm:artistName(?artist) WHERE { ?album nmm:albumArtist ?artist } LIMIT 1) AS artist nie:title(?album) as title nie:title(?album) as album tracker:coalesce( (SELECT GROUP_CONCAT(nmm:artistName(?artist), ",") WHERE { ?album nmm:albumArtist ?artist }), (SELECT GROUP_CONCAT((SELECT nmm:artistName(nmm:performer(?_12)) as perf WHERE { ?_12 nmm:musicAlbum ?album } GROUP BY ?perf), ",") as album_performer WHERE { }) ) as author xsd:integer(tracker:coalesce(nmm:albumTrackCount(?album), (SELECT COUNT(?_1) WHERE { ?_1 nmm:musicAlbum ?album; tracker:available "true" }))) as childcount (SELECT fn:year-from-dateTime(?c) WHERE { ?_2 nmm:musicAlbum ?album; nie:contentCreated ?c; tracker:available "true" } LIMIT 1) as creation-date { ?album a nmm:MusicAlbum FILTER (EXISTS { ?_3 nmm:musicAlbum ?album; tracker:available "true" }) } ORDER BY nie:title(?album) ?author ?albumyear';

const artist = 'SELECT DISTINCT rdf:type(?album) tracker:id(?album) as id (SELECT nmm:artistName(?artist) WHERE { ?album nmm:albumArtist ?artist } LIMIT 1) AS artist nie:title(?album) as title nie:title(?album) as album tracker:coalesce( (SELECT GROUP_CONCAT(nmm:artistName(?artist), ",") WHERE { ?album nmm:albumArtist ?artist }), (SELECT GROUP_CONCAT((SELECT nmm:artistName(nmm:performer(?_12)) as perf WHERE { ?_12 nmm:musicAlbum ?album } GROUP BY ?perf), ",") as album_performer WHERE { }) ) as author xsd:integer(tracker:coalesce(nmm:albumTrackCount(?album), (SELECT COUNT(?_1) WHERE { ?_1 nmm:musicAlbum ?album; tracker:available "true" }))) as childcount (SELECT fn:year-from-dateTime(?c) WHERE { ?_2 nmm:musicAlbum ?album; nie:contentCreated ?c; tracker:available "true" } LIMIT 1) as creation-date { ?album a nmm:MusicAlbum FILTER (EXISTS { ?_3 nmm:musicAlbum ?album; tracker:available "true" }) } ORDER BY ?author ?albumyear nie:title(?album)';

const album_count = 'SELECT COUNT(?album) AS childcount WHERE { ?album a nmm:MusicAlbum }';

const artist_count = 'SELECT COUNT(DISTINCT ?artist) WHERE { ?artist a nmm:Artist . ?album nmm:performer ?artist }';

/*const songs = 'SELECT DISTINCT rdf:type(?song) tracker:id(?song) as id nie:url(?song) as url nie:title(?song) as title nmm:artistName(nmm:performer(?song)) as artist nie:title(nmm:musicAlbum(?song)) as album nfo:duration(?song) as duration { ?song a nmm:MusicPiece } (SELECT fn:year-from-dateTime(?c) WHERE { ?_2 nmm:musicAlbum(?song); nie:contentCreated ?c; tracker:available "true" } LIMIT 1) as creation-date ORDER BY tracker:added(?song)';*/

const songs = 'SELECT DISTINCT rdf:type(?song) tracker:id(?song) as id nie:url(?song) as url nie:title(?song) as title nmm:artistName(nmm:performer(?song)) as artist nie:title(nmm:musicAlbum(?song)) as album nfo:duration(?song) as duration { ?song a nmm:MusicPiece } ORDER BY tracker:added(?song)';

const songs_count = 'SELECT COUNT(?song) AS childcount WHERE { ?song a nmm:MusicPiece }';

function album_songs (album_id) {
    var query = "SELECT DISTINCT rdf:type(?song) tracker:id(?song) as id nie:url(?song) as url nie:title(?song) as title nmm:artistName(nmm:performer(?song)) as artist nie:title(nmm:musicAlbum(?song)) as album nfo:duration(?song) as duration WHERE { ?song a nmm:MusicPiece ; nmm:musicAlbum ?album . filter (tracker:id(?album) ="+ album_id +") } ORDER BY nmm:trackNumber(?song) tracker:added(?song)";
    return query;
}
