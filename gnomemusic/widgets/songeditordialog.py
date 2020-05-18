# Copyright 2022 The GNOME Music Developers
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

from __future__ import annotations
from gettext import gettext as _, ngettext
from itertools import chain
from typing import Callable, Dict, List, NamedTuple, Optional
import typing

from gi.repository import Gtk, Gio, GObject, GLib, Grl

from gnomemusic.utils import ArtSize
from gnomemusic.widgets.artstack import ArtStack  # noqa: F401
from gnomemusic.widgets.notificationspopup import TagEditorNotification
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coregrilo import CoreGrilo
    from gnomemusic.coresong import CoreSong
    from gnomemusic.musiclogger import MusicLogger

import gnomemusic.utils as utils


@Gtk.Template(resource_path="/org/gnome/Music/ui/SongEditorDialog.ui")
class SongEditorDialog(Gtk.Dialog):
    """Song tag editor widget
    A tag editor dialog box that allows storing metadata for music files
    through editing entries manually or applying automatic fetched tags.
    """

    __gtype_name__ = "SongEditorDialog"

    _art_stack = Gtk.Template.Child()
    _next_button = Gtk.Template.Child()
    _notifications_popup = Gtk.Template.Child()
    _prev_button = Gtk.Template.Child()
    _spinner = Gtk.Template.Child()
    _state_label = Gtk.Template.Child()
    _submit_button = Gtk.Template.Child()
    _suggestion_label = Gtk.Template.Child()
    _url_label = Gtk.Template.Child()
    _use_suggestion_button = Gtk.Template.Child()

    # tags entries and labels
    _album_artist_entry = Gtk.Template.Child()
    _album_artist_suggestion = Gtk.Template.Child()
    _album_entry = Gtk.Template.Child()
    _album_suggestion = Gtk.Template.Child()
    _artist_entry = Gtk.Template.Child()
    _artist_suggestion = Gtk.Template.Child()
    _disc_entry = Gtk.Template.Child()
    _disc_suggestion = Gtk.Template.Child()
    _title_entry = Gtk.Template.Child()
    _title_suggestion = Gtk.Template.Child()
    _track_entry = Gtk.Template.Child()
    _track_suggestion = Gtk.Template.Child()
    _year_entry = Gtk.Template.Child()
    _year_suggestion = Gtk.Template.Child()

    __gsignals__ = {
        "no-tags": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    class Tag(NamedTuple):
        name: str
        getter: Callable[[Grl.Media], str]
        setter: Callable[[Grl.Media, str], None]
        grl_key: int

    _tags: List[Tag] = [
        Tag("album", utils.get_album_title, Grl.Media.set_album,
            Grl.METADATA_KEY_ALBUM),
        Tag("album_artist", utils.get_album_artist,
            Grl.Media.set_album_artist, Grl.METADATA_KEY_ALBUM_ARTIST),
        Tag("artist", utils.get_song_artist, Grl.Media.set_artist,
            Grl.METADATA_KEY_ARTIST),
        Tag("disc", utils.get_album_disc_nr, utils.set_album_disc_nr,
            Grl.METADATA_KEY_ALBUM_DISC_NUMBER),
        Tag("title", utils.get_media_title, Grl.Media.set_title,
            Grl.METADATA_KEY_TITLE),
        Tag("track", utils.get_media_track_nr, utils.set_media_track_nr,
            Grl.METADATA_KEY_TRACK_NUMBER),
        Tag("year", utils.get_media_year, utils.set_media_year,
            Grl.METADATA_KEY_PUBLICATION_DATE)
    ]

    _internal_tags: List[Tag] = [
        Tag("mb-recording-id", Grl.Media.get_mb_recording_id,
            Grl.Media.set_mb_recording_id, Grl.METADATA_KEY_MB_RECORDING_ID),
        Tag("mb-track-id", Grl.Media.get_mb_track_id,
            Grl.Media.set_mb_track_id, Grl.METADATA_KEY_MB_TRACK_ID),
        Tag("mb-artist-id", Grl.Media.get_mb_artist_id,
            Grl.Media.set_mb_artist_id, Grl.METADATA_KEY_MB_ARTIST_ID),
        Tag("mb-release-id", Grl.Media.get_mb_release_id,
            Grl.Media.set_mb_release_id, Grl.METADATA_KEY_MB_RELEASE_ID),
        Tag("mb-release-group-id", Grl.Media.get_mb_release_group_id,
            Grl.Media.set_mb_release_group_id,
            Grl.METADATA_KEY_MB_RELEASE_GROUP_ID)
    ]

    def __init__(
            self, application: Application, selected_song: CoreSong) -> None:
        """Initialize the tag editor

        :param Application application: Application object
        :param Coresong selected_song: The Song being edited
        """
        super().__init__()

        self._coregrilo: CoreGrilo = application.props.coregrilo
        self._log: MusicLogger = application.props.log

        self._art_stack.props.size = ArtSize.LARGE
        self._art_stack.props.coreobject = selected_song

        music_dir: str = GLib.UserDirectory.DIRECTORY_MUSIC
        self._music_directory: str = GLib.get_user_special_dir(music_dir)

        self._coresong: CoreSong = selected_song
        self._init_labels()

        self._notification: Optional[TagEditorNotification] = None
        self._notification_finished_id: int = 0
        self._notification_undo_id: int = 0

        self._previous_tags: Dict[str, str] = {}
        self._suggestions: List[Grl.Media] = []
        self._suggestion_idx: int = -1
        self._chosen_suggestion_idx: int = -1
        self._search_tags()

    def _init_labels(self) -> None:
        for tag in self._tags:
            entry: Gtk.Entry = getattr(self, "_" + tag.name + "_entry")
            value: str = tag.getter(self._coresong.props.media)
            if value:
                entry.props.text = value
            entry.connect("notify::text", self._on_entries_changed)

        file_: Gio.File = Gio.File.new_for_uri(self._coresong.props.url)
        file_path: str = file_.get_path()
        if file_path.startswith(self._music_directory):
            baselength: int = len(self._music_directory) + 1
            self._url_label.props.label = file_path[baselength:]
            self._url_label.props.tooltip_text = file_path[baselength:]
        else:
            self._url_label.props.label = file_path
            self._url_label.props.tooltip_text = file_path

        self._url_label.props.has_tooltip = True
        self._url_label.props.visible = True

    def _start_spinner(self) -> None:
        self._spinner.start()
        self._state_label.props.label = _("Fetching metadata…")

    def _stop_spinner(self) -> None:
        self._spinner.stop()
        label: str = _("No suggestions found")
        if self._suggestions:
            label = ngettext(
                "{} suggestion found", "{} suggestions found",
                len(self._suggestions)).format(len(self._suggestions))

        self._state_label.props.label = label

    def _search_tags(self) -> None:
        self._start_spinner()
        self._coresong.query_musicbrainz_tags(self._tags_found)

    def _suggestion_sort_func(self, media: Grl.Media) -> GLib.DateTime:
        creation_date: Optional[GLib.DateTime] = media.get_creation_date()
        if creation_date:
            return (creation_date.get_year(), media.get_album())

        return (GLib.DateTime.new_now_utc().get_year(), media.get_album())

    def _tags_found(self, media: Optional[Grl.Media], count: int = 0) -> None:
        if not media:
            self._log.warning(
                "Unable to find tags for song {}".format(
                    self._coresong.props.url))
            self._stop_spinner()
            self._create_notification(TagEditorNotification.Type.NONE)
            return

        self._suggestions.append(media)

        if count == 0:
            self._suggestions.sort(key=self._suggestion_sort_func)
            self._stop_spinner()
            self._suggestion_idx = 0
            self._update_suggestion()
            self._on_entries_changed()

    def _update_suggestion(self) -> None:
        media: Grl.Media = self._suggestions[self._suggestion_idx]
        for tag in self._tags:
            label: Grl.Label = getattr(self, "_" + tag.name + "_suggestion")
            value: str = tag.getter(media)
            if value:
                label.props.label = value
                label.props.visible = True
                label.props.has_tooltip = True
                label.props.tooltip_text = value

        nr_results: int = len(self._suggestions)
        self._next_button.props.sensitive = (
            self._suggestion_idx < len(self._suggestions) - 1)
        self._prev_button.props.sensitive = (self._suggestion_idx > 0)

        if nr_results > 1:
            idx: int = self._suggestion_idx + 1
            suggestion_txt: str = "({}/{})".format(idx, nr_results)
            self._suggestion_label.props.label = suggestion_txt
            self._suggestion_label.props.visible = True

    def _on_entries_changed(
            self, widget: Optional[Gtk.Entry] = None,
            param: Optional[GObject.GParamSpec] = None) -> None:
        if self._suggestion_idx >= 0:
            media: Grl.Media = self._suggestions[self._suggestion_idx]
            self._use_suggestion_button.props.sensitive = False
        self._submit_button.props.sensitive = False

        for tag in self._tags:
            entry: Gtk.Entry = getattr(self, "_" + tag.name + "_entry")
            value: str = tag.getter(self._coresong.props.media)
            typed_value: str = entry.props.text.strip()
            if (typed_value
                    and value != typed_value):
                self._submit_button.props.sensitive = True
            if self._suggestion_idx >= 0:
                suggested_value = tag.getter(media)
                if (typed_value
                        and suggested_value
                        and typed_value != suggested_value):
                    self._use_suggestion_button.props.sensitive = True

    @Gtk.Template.Callback()
    def _on_next_button_clicked(self, widget: Gtk.Button) -> None:
        self._suggestion_idx += 1
        self._update_suggestion()
        self._on_entries_changed()

    @Gtk.Template.Callback()
    def _on_prev_button_clicked(self, widget: Gtk.Button) -> None:
        self._suggestion_idx -= 1
        self._update_suggestion()
        self._on_entries_changed()

    @Gtk.Template.Callback()
    def _on_use_suggestion_clicked(self, widget: Gtk.Button) -> None:
        suggested_media: Grl.Media = self._suggestions[self._suggestion_idx]
        self._previous_tags.clear()
        for tag in self._tags:
            entry: Gtk.Entry = getattr(self, "_" + tag.name + "_entry")
            self._previous_tags[tag.name] = entry.props.text
            suggested_value: str = tag.getter(suggested_media)
            if suggested_value:
                entry.props.text = suggested_value

        self._chosen_suggestion_idx = self._suggestion_idx
        self._create_notification(TagEditorNotification.Type.SONG)
        self._on_entries_changed()

    def _create_notification(
            self, notification_type: TagEditorNotification.Type) -> None:
        self._notification = TagEditorNotification(
            self._notifications_popup, notification_type)
        if notification_type != TagEditorNotification.Type.NONE:
            self._notification_undo_id = self._notification.connect(
                "undo-fill", self._undo_use_suggestion)

        self._notification_finished_id = self._notification.connect(
            "finished", self._delete_notification)

    def _delete_notification(
            self,
            notification: Optional[TagEditorNotification] = None) -> None:
        if not self._notification:
            return

        if self._notification_undo_id != 0:
            self._notification.disconnect(self._notification_undo_id)
            self._notification_undo_id = 0

        self._notification.disconnect(self._notification_finished_id)
        self._notification_finished_id = 0
        self._notification = None

    def _undo_use_suggestion(
            self, notification: TagEditorNotification) -> None:
        """Revert found_tags filling

        :param TagEditorNotification notification: the notification
        """
        for tag in self._tags:
            entry: Gtk.Entry = getattr(self, "_" + tag.name + "_entry")
            entry.props.text = self._previous_tags[tag.name]

        self._chosen_suggestion_idx = -1
        self._delete_notification()

    @Gtk.Template.Callback()
    def _on_submit_clicked(self, widget: Gtk.Button) -> None:
        self._delete_notification()

        changed_tags_keys: List[int] = []
        media_writeback: Grl.Media = Grl.Media.audio_new()

        # If _chosen_suggestion_idx is greater than -1, an online
        # suggestion has been chosen. Otherwise, the tags have been
        # manually changed.
        chosen_idx: int = self._chosen_suggestion_idx
        if chosen_idx > -1:
            media_chosen: Grl.Media = self._suggestions[chosen_idx]
            for tag in chain(self._tags, self._internal_tags):
                existing_tag_text: str = tag.getter(self._coresong.props.media)
                new_tag_text: str = tag.getter(media_chosen)
                if new_tag_text:
                    tag.setter(media_writeback, new_tag_text)
                    if new_tag_text != existing_tag_text:
                        changed_tags_keys.append(tag.grl_key)
        else:
            for tag in self._tags:
                existing_tag_text = tag.getter(self._coresong.props.media)
                entry: Gtk.Entry = getattr(self, "_" + tag.name + "_entry")
                new_tag_text = entry.props.text.strip()
                if new_tag_text:
                    tag.setter(media_writeback, new_tag_text)
                    if new_tag_text != existing_tag_text:
                        changed_tags_keys.append(tag.grl_key)

        if changed_tags_keys:
            media_writeback.set_source(self._coresong.props.media.get_source())
            media_writeback.set_url(self._coresong.props.media.get_url())

            # FIXME: (Grilo tracker3 plugin). If the musicbrainz
            # release or release group tag is updated, the album key
            # need to be added to the list of changed keys to update
            # those tags.
            # For similar reasons, the artist key also needs to be
            # added if the musicbrainz artist tag is updated.
            if ((Grl.METADATA_KEY_MB_RELEASE_ID in changed_tags_keys
                 or Grl.METADATA_KEY_MB_RELEASE_GROUP_ID in changed_tags_keys)
                    and Grl.METADATA_KEY_ALBUM not in changed_tags_keys):
                changed_tags_keys.append(Grl.METADATA_KEY_ALBUM)

            if (Grl.METADATA_KEY_MB_ARTIST_ID in changed_tags_keys
                    and Grl.METADATA_KEY_ARTIST not in changed_tags_keys):
                changed_tags_keys.append(Grl.METADATA_KEY_ARTIST)

            self._log.debug(
                "Updating tags for song {}".format(self._coresong.props.url))
            self._coregrilo.writeback(media_writeback, changed_tags_keys)
        else:
            self._log.debug(
                "No updated tag for song {}".format(self._coresong.props.url))

        self.response(Gtk.ResponseType.ACCEPT)
