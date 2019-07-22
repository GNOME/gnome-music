# Copyright 2018 The GNOME Music Developers
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

from gi.repository import Grl, Gtk, Gio, GLib

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.grilo import grilo
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/org/gnome/Music/ui/TagEditorDialog.ui")
class TagEditorDialog(Gtk.Dialog):
    """Tag editor widget
    A tag editor dialog box that allows storing metadata for music files
    through editing entries manually or applying automatic fetched tags.
    """

    __gtype_name__ = 'TagEditorDialog'

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

    def __repr__(self):
        return '<TagEditorDialog>'

    @log
    def __init__(self, parent, selected_song):
        """Initialize the tag editor
        :param parent: The parent widget calling the editor dialog box
        :param selected_song: The current selected track which is being edited
        """
        super().__init__()

        self.props.transient_for = parent
        self.set_titlebar(self._title_bar)

        self._cover_stack.props.size = Art.Size.MEDIUM
        self._cover_stack.update(selected_song)

        self._music_directory = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)

        self._initial_song = selected_song
        self._init_labels()
        self._search_tags()
        self._suggestions = []
        self._pointer = 0

    @log
    def _init_labels(self):
        for field in utils.fields_getter:
            entry = getattr(self, '_' + field + '_entry')
            value = utils.fields_getter[field](self._initial_song)
            if value:
                entry.props.text = value
            entry.connect('notify::text', self._on_entries_changed)

        file_url = self._initial_song.get_url()
        file_ = Gio.File.new_for_uri(file_url)
        file_path = file_.get_path()
        if file_path.startswith(self._music_directory):
            self._url.set_text(file_path[len(self._music_directory)+1:])
        else:
            self._url.set_text(file_path)
        self._url.props.visible = True

    @log
    def _start_spinner(self, text):
        self._spinner.start()
        self._spinner_label.props.label = text

    @log
    def _stop_spinner(self):
        self._spinner.stop()
        self._spinner_label.props.label = ""

    @log
    def _search_tags(self):
        self._start_spinner(_("Fetching metadata…"))
        new_media = Grl.Media.audio_new()
        new_media.set_url(self._initial_song.get_url())
        grilo.get_tags_from_musicbrainz(new_media, self._tags_found)

    @log
    def _tags_found(self, media, count):
        if media is None:
            logger.warning("Unable to find tags for song {}".format(
                self._initial_song.get_url()))
            self._stop_spinner()
            return

        self._use_suggestion_button.props.sensitive = True
        self._suggestions.append(media)

        if count == 0:
            self._give_suggestion()
            self._stop_spinner()

    @log
    def _give_suggestion(self):
        media = self._suggestions[self._pointer]
        for field in utils.fields_getter:
            suggestion = getattr(self, '_' + field + '_suggestion')
            value = utils.fields_getter[field](media)
            if value:
                suggestion.props.label = value
                suggestion.props.visible = True

        if self._pointer < len(self._suggestions) - 1:
            self._next_button.props.sensitive = True
        else:
            self._next_button.props.sensitive = False

        if self._pointer > 0:
            self._prev_button.props.sensitive = True
        else:
            self._prev_button.props.sensitive = False

    @log
    def _on_entries_changed(self, widget, param):
        self._submit_button.props.sensitive = False
        for field in utils.fields_getter:
            entry = getattr(self, '_' + field + '_entry')
            value = utils.fields_getter[field](self._initial_song)
            typed_value = entry.get_text().strip()
            if typed_value and value != typed_value:
                self._submit_button.props.sensitive = True
                break

    @Gtk.Template.Callback()
    @log
    def _on_next_button_clicked(self, widget):
        self._pointer += 1
        self._give_suggestion()

    @Gtk.Template.Callback()
    @log
    def _on_prev_button_clicked(self, widget):
        self._pointer -= 1
        self._give_suggestion()

    @Gtk.Template.Callback()
    @log
    def _on_use_suggestion_clicked(self, widget):
        media = self._suggestions[self._pointer]

        for field in utils.fields_getter:
            entry = getattr(self, '_' + field + '_entry')
            value = utils.fields_getter[field](media)
            if value:
                entry.set_text(value)

    @Gtk.Template.Callback()
    @log
    def _on_submit_clicked(self, widget):

        for field in utils.fields_setter:
            entry = getattr(self, '_' + field + '_entry')
            entry_text = entry.get_text()
            if entry_text:
                utils.fields_setter[field](self._initial_song, entry_text)

        self.destroy()
