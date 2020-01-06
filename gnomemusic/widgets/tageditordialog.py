# Copyright 2019 The GNOME Music Developers
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

import logging
from gettext import gettext as _

from gi.repository import Gtk, Gio, GObject, GLib

from gnomemusic.albumartcache import Art
from gnomemusic.widgets.notificationspopup import TagEditorNotification

import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/org/gnome/Music/ui/TagEditorDialog.ui")
class TagEditorDialog(Gtk.Dialog):
    """Tag editor widget
    A tag editor dialog box that allows storing metadata for music files
    through editing entries manually or applying automatic fetched tags.
    """

    __gtype_name__ = "TagEditorDialog"

    _notifications_popup = Gtk.Template.Child()

    _cover_stack = Gtk.Template.Child()
    _spinner = Gtk.Template.Child()
    _spinner_label = Gtk.Template.Child()
    _title_bar = Gtk.Template.Child()

    # tags entries and labels
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
    _prev_button = Gtk.Template.Child()
    _next_button = Gtk.Template.Child()
    _use_suggestion_button = Gtk.Template.Child()
    _submit_button = Gtk.Template.Child()

    _url = Gtk.Template.Child()

    __gsignals__ = {
        "no-tags": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return "<TagEditorDialog>"

    def __init__(self, parent, selected_song, grilo, coreselection):
        """Initialize the tag editor
        :param parent: The parent widget calling the editor dialog box
        :param selected_song: The current selected track which is being edited
        """
        super().__init__()

        self._grilo = grilo
        self._coreselection = coreselection

        self.props.transient_for = parent
        self.set_titlebar(self._title_bar)

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
        self._pointer = -1
        self._search_tags()

    def _init_labels(self):
        for field in utils.fields_getter:
            entry = getattr(self, "_" + field + "_entry")
            value = utils.fields_getter[field](self._coresong.props.media)
            if value:
                entry.props.text = value
            entry.connect("notify::text", self._on_entries_changed)

        file_ = Gio.File.new_for_uri(self._coresong.props.url)
        file_path = file_.get_path()
        if file_path.startswith(self._music_directory):
            baselength = len(self._music_directory) + 1
            self._url.set_text(file_path[baselength:])
            self._url.props.tooltip_text = file_path[baselength:]
        else:
            self._url.set_text(file_path)
            self._url.props.tooltip_text = file_path

        self._url.props.has_tooltip = True
        self._url.props.visible = True

    def _start_spinner(self, text):
        self._spinner.start()
        self._spinner_label.props.label = text

    def _stop_spinner(self):
        self._spinner.stop()
        self._spinner_label.props.label = ""

    def _search_tags(self):
        self._start_spinner(_("Fetching metadata…"))
        self._coresong.query_musicbrainz_tags(self._tags_found)

    def _suggestion_sort_func(self, media):
        creation_date = media.get_creation_date()
        if creation_date is not None:
            return (creation_date.get_year(), media.get_album())
        return (GLib.DateTime.new_now_utc().get_year(), media.get_album())

    def _tags_found(self, media, count=0):
        if media is None:
            logger.warning("Unable to find tags for song {}".format(
                self._coresong.props.url))
            self._stop_spinner()
            self._create_notification(TagEditorNotification.Type.NONE)
            return

        self._suggestions.append(media)

        if count == 0:
            self._suggestions.sort(key=self._suggestion_sort_func)
            self._stop_spinner()
            self._pointer = 0
            self._update_suggestion()
            self._on_entries_changed()

    def _update_suggestion(self):
        media = self._suggestions[self._pointer]
        for field in utils.fields_getter:
            suggestion = getattr(self, "_" + field + "_suggestion")
            value = utils.fields_getter[field](media)
            if value:
                suggestion.props.label = value
                suggestion.props.visible = True
                suggestion.props.has_tooltip = True
                suggestion.props.tooltip_text = value

        self._next_button.props.sensitive = (
            self._pointer < len(self._suggestions) - 1)
        self._prev_button.props.sensitive = (self._pointer > 0)

    def _on_entries_changed(self, widget=None, param=None):
        if self._pointer >= 0:
            media = self._suggestions[self._pointer]
            self._use_suggestion_button.props.sensitive = False
        self._submit_button.props.sensitive = False

        for field in utils.fields_getter:
            entry = getattr(self, "_" + field + "_entry")
            value = utils.fields_getter[field](self._coresong.props.media)
            typed_value = entry.props.text.strip()
            if (typed_value
                    and value != typed_value):
                self._submit_button.props.sensitive = True
            if self._pointer >= 0:
                suggested_value = utils.fields_getter[field](media)
                if (typed_value
                        and suggested_value
                        and typed_value != suggested_value):
                    self._use_suggestion_button.props.sensitive = True

    @Gtk.Template.Callback()
    def _on_next_button_clicked(self, widget):
        self._pointer += 1
        self._update_suggestion()
        self._on_entries_changed()

    @Gtk.Template.Callback()
    def _on_prev_button_clicked(self, widget):
        self._pointer -= 1
        self._update_suggestion()
        self._on_entries_changed()

    @Gtk.Template.Callback()
    def _on_use_suggestion_clicked(self, widget):
        suggested_media = self._suggestions[self._pointer]
        self._previous_tags.clear()
        for field in utils.fields_getter:
            entry = getattr(self, "_" + field + "_entry")
            self._previous_tags[field] = entry.props.text
            suggested_value = utils.fields_getter[field](suggested_media)
            if suggested_value:
                entry.props.text = suggested_value

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
        if self._notification is None:
            return

        if self._notification_undo_id is not None:
            self._notification.disconnect(self._notification_undo_id)
            self._notification_undo_id = None

        self._notification.disconnect(self._notification_finished_id)
        self._notification_finished_id = None
        self._notification = None

    def _undo_use_suggestion(self, notification):
        """Revert tags filling

        :param TagEditorNotification notification: the notification
        """
        for field in utils.fields_getter:
            entry = getattr(self, "_" + field + "_entry")
            entry.props.text = self._previous_tags[field]

        self._delete_notification()

    @Gtk.Template.Callback()
    def _on_submit_clicked(self, widget):
        self._delete_notification()

        for field in self._coresong.fields_setter:
            entry = getattr(self, "_" + field + "_entry")
            entry_text = entry.props.text
            if entry_text:
                self._coresong.fields_setter[field](entry_text)

        self.destroy()
