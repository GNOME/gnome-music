/*
* Copyright (c) 2013 Igalia S.L.
* Authored by: Juan A. Suarez Romero <jasuarez@igalia.com>
*
* Gnome Music is free software; you can Public License as published by the
* Free Software Foundation; either version 2 of the License, or (at your
* option) any later version.
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

const album = 'SELECT DISTINCT rdf:type(?album) tracker:id(?album) as id (SELECT nmm:artistName(?artist) WHERE { ?album nmm:albumArtist ?artist } LIMIT 1) AS artist nie:title(?album) as title nie:title(?album) as album tracker:coalesce( (SELECT GROUP_CONCAT(nmm:artistName(?artist), ",") WHERE { ?album nmm:albumArtist ?artist }), (SELECT GROUP_CONCAT((SELECT nmm:artistName(nmm:performer(?_12)) as perf WHERE { ?_12 nmm:musicAlbum ?album } GROUP BY ?perf), ",") as album_performer WHERE { }) ) as author xsd:integer(tracker:coalesce(nmm:albumTrackCount(?album), (SELECT COUNT(?_1) WHERE { ?_1 nmm:musicAlbum ?album; tracker:available "true" }))) as childcount (SELECT fn:year-from-dateTime(?c) WHERE { ?_2 nmm:musicAlbum ?album; nie:contentCreated ?c; tracker:available "true" } LIMIT 1) as publishing-date { ?album a nmm:MusicAlbum FILTER (EXISTS { ?_3 nmm:musicAlbum ?album; tracker:available "true" }) } ORDER BY ?album_artist ?albumyear nie:title(?album)';

const album_count = 'SELECT COUNT(?album) AS childcount WHERE { ?album a nmm:MusicAlbum }';

const songs = 'SELECT DISTINCT rdf:type(?song) tracker:id(?song) as id nie:url(?song) as url nie:title(?song) as title nmm:artistName(nmm:performer(?song)) as artist nie:title(nmm:musicAlbum(?song)) as album nfo:duration(?song) as duration { ?song a nmm:MusicPiece } ORDER BY tracker:added(?song)';

const songs_count = 'SELECT COUNT(?song) AS childcount WHERE { ?song a nmm:MusicPiece }';

function album_songs (album_id) {
    var query = "SELECT DISTINCT rdf:type(?song) tracker:id(?song) as id nie:url(?song) as url nie:title(?song) as title nmm:artistName(nmm:performer(?song)) as artist nie:title(nmm:musicAlbum(?song)) as album nfo:duration(?song) as duration WHERE { ?song a nmm:MusicPiece ; nmm:musicAlbum ?album . filter (tracker:id(?album) ="+ album_id +") } ORDER BY nmm:trackNumber(?song) tracker:added(?song)";
    return query;
}
