# Copyright 2020 The GNOME Music Developers
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

from gettext import gettext as _, ngettext

from gi.repository import Gtk, Gio, GObject, GLib

from gnomemusic.albumartcache import Art
from gnomemusic.widgets.notificationspopup import TagEditorNotification

import gnomemusic.utils as utils


@Gtk.Template(resource_path="/org/gnome/Music/ui/SongEditorDialog.ui")
class SongEditorDialog(Gtk.Dialog):
    """Song tag editor widget
    A tag editor dialog box that allows storing metadata for music files
    through editing entries manually or applying automatic fetched tags.
    """

    __gtype_name__ = "SongEditorDialog"

    _cover_stack = Gtk.Template.Child()
    _next_button = Gtk.Template.Child()
    _notifications_popup = Gtk.Template.Child()
    _prev_button = Gtk.Template.Child()
    _spinner = Gtk.Template.Child()
    _spinner_label = Gtk.Template.Child()
    _submit_button = Gtk.Template.Child()
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

    _fields_getter = {
        "album": utils.get_album_title,
        "album_artist": utils.get_album_artist,
        "artist": utils.get_song_artist,
        "disc": utils.get_album_disc_nr,
        "title": utils.get_media_title,
        "track": utils.get_media_track_nr,
        "year": utils.get_media_year
    }

    def __init__(self, application, selected_song):
        """Initialize the tag editor
        :param Application application: Application object
        :param Coresong selected_song: The Song being edited
        """
        super().__init__()

        self._log = application.props.log

        self._cover_stack.props.size = Art.Size.LARGE
        self._cover_stack.update(selected_song)

        music_dir = GLib.UserDirectory.DIRECTORY_MUSIC
        self._music_directory = GLib.get_user_special_dir(music_dir)

        self._coresong = selected_song
        self._init_labels()

        self._notification = None
        self._notification_finished_id = None
        self._notification_undo_id = None

        self._previous_tags = {}
        self._suggestions = []
        self._suggestion_index = -1
        self._chosen_suggestion_index = -1
        self._search_tags()

    def _init_labels(self):
        for field in self._fields_getter:
            entry = getattr(self, "_" + field + "_entry")
            value = self._fields_getter[field](self._coresong.props.media)
            if value:
                entry.props.text = value
            entry.connect("notify::text", self._on_entries_changed)

        file_ = Gio.File.new_for_uri(self._coresong.props.url)
        file_path = file_.get_path()
        if file_path.startswith(self._music_directory):
            baselength = len(self._music_directory) + 1
            self._url_label.props.label = file_path[baselength:]
            self._url_label.props.tooltip_text = file_path[baselength:]
        else:
            self._url_label.props.label = file_path
            self._url_label.props.tooltip_text = file_path

        self._url_label.props.has_tooltip = True
        self._url_label.props.visible = True

    def _start_spinner(self):
        self._spinner.start()
        self._spinner_label.props.label = _("Fetching metadata…")

    def _stop_spinner(self):
        self._spinner.stop()
        label = _("No suggestions found")
        if self._suggestions:
            label = ngettext(
                "{} suggestion found", "{} suggestions found",
                len(self._suggestions)).format(len(self._suggestions))

        self._spinner_label.props.label = label

    def _search_tags(self):
        self._start_spinner()
        self._coresong.query_musicbrainz_tags(self._tags_found)

    def _suggestion_sort_func(self, media):
        creation_date = media.get_creation_date()
        if creation_date:
            return (creation_date.get_year(), media.get_album())
        return (GLib.DateTime.new_now_utc().get_year(), media.get_album())

    def _tags_found(self, media, count=0):
        if not media:
            self._log.warning("Unable to find tags for song {}".format(
                self._coresong.props.url))
            self._stop_spinner()
            self._create_notification(TagEditorNotification.Type.NONE)
            return

        self._suggestions.append(media)

        if count == 0:
            self._suggestions.sort(key=self._suggestion_sort_func)
            self._stop_spinner()
            self._suggestion_index = 0
            self._update_suggestion()
            self._on_entries_changed()

    def _update_suggestion(self):
        media = self._suggestions[self._suggestion_index]
        for field in self._fields_getter:
            suggestion = getattr(self, "_" + field + "_suggestion")
            value = self._fields_getter[field](media)
            if value:
                suggestion.props.label = value
                suggestion.props.visible = True
                suggestion.props.has_tooltip = True
                suggestion.props.tooltip_text = value

        self._next_button.props.sensitive = (
            self._suggestion_index < len(self._suggestions) - 1)
        self._prev_button.props.sensitive = (self._suggestion_index > 0)

    def _on_entries_changed(self, widget=None, param=None):
        if self._suggestion_index >= 0:
            media = self._suggestions[self._suggestion_index]
            self._use_suggestion_button.props.sensitive = False
        self._submit_button.props.sensitive = False

        for field in self._fields_getter:
            entry = getattr(self, "_" + field + "_entry")
            value = self._fields_getter[field](self._coresong.props.media)
            typed_value = entry.props.text.strip()
            if (typed_value
                    and value != typed_value):
                self._submit_button.props.sensitive = True
            if self._suggestion_index >= 0:
                suggested_value = self._fields_getter[field](media)
                if (typed_value
                        and suggested_value
                        and typed_value != suggested_value):
                    self._use_suggestion_button.props.sensitive = True

    @Gtk.Template.Callback()
    def _on_next_button_clicked(self, widget):
        self._suggestion_index += 1
        self._update_suggestion()
        self._on_entries_changed()

    @Gtk.Template.Callback()
    def _on_prev_button_clicked(self, widget):
        self._suggestion_index -= 1
        self._update_suggestion()
        self._on_entries_changed()

    @Gtk.Template.Callback()
    def _on_use_suggestion_clicked(self, widget):
        suggested_media = self._suggestions[self._suggestion_index]
        self._previous_tags.clear()
        for field in self._fields_getter:
            entry = getattr(self, "_" + field + "_entry")
            self._previous_tags[field] = entry.props.text
            suggested_value = self._fields_getter[field](suggested_media)
            if suggested_value:
                entry.props.text = suggested_value

        self._chosen_suggestion_index = self._suggestion_index
        self._create_notification(TagEditorNotification.Type.SONG)
        self._on_entries_changed()

    def _create_notification(self, notification_type):
        self._notification = TagEditorNotification(
            self._notifications_popup, notification_type)
        if notification_type != TagEditorNotification.Type.NONE:
            self._notification_undo_id = self._notification.connect(
                "undo-fill", self._undo_use_suggestion)

        self._notification_finished_id = self._notification.connect(
            "finished", self._delete_notification)

    def _delete_notification(self, notification=None):
        if not self._notification:
            return

        if self._notification_undo_id:
            self._notification.disconnect(self._notification_undo_id)
            self._notification_undo_id = None

        self._notification.disconnect(self._notification_finished_id)
        self._notification_finished_id = None
        self._notification = None

    def _undo_use_suggestion(self, notification):
        """Revert tags filling

        :param TagEditorNotification notification: the notification
        """
        for field in self._fields_getter:
            entry = getattr(self, "_" + field + "_entry")
            entry.props.text = self._previous_tags[field]

        self._chosen_suggestion_index = -1
        self._delete_notification()

    @Gtk.Template.Callback()
    def _on_submit_clicked(self, widget):
        self._delete_notification()

        tags = {
            "mb-recording-id": None,
            "mb-track-id": None,
            "mb-artist-id": None,
            "mb-release-id": None,
            "mb-release-group-id": None
        }

        for field in self._fields_getter:
            entry = getattr(self, "_" + field + "_entry")
            tag_key = field.replace("_", "-")
            tags[tag_key] = entry.props.text

        if self._chosen_suggestion_index > -1:
            media = self._suggestions[self._chosen_suggestion_index]
            tags["mb-recording-id"] = media.get_mb_recording_id()
            tags["mb-track-id"] = media.get_mb_track_id()
            tags["mb-artist-id"] = media.get_mb_artist_id()
            tags["mb-release-id"] = media.get_mb_release_id()
            tags["mb-release-group-id"] = media.get_mb_release_group_id()

        self._coresong.update_tags(tags)
        self.response(Gtk.ResponseType.ACCEPT)
