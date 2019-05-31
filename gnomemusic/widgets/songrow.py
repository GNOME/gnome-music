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

from enum import IntEnum

from gi.repository import Gdk, GObject, Grl, Gtk

from gnomemusic import utils
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists, SmartPlaylists
from gnomemusic.widgets.starimage import StarImage  # noqa: F401


@Gtk.Template(resource_path="/org/gnome/Music/ui/SongRow.ui")
class SongRow(Gtk.ListBoxRow):
    """The single song row used in PlaylistView

    Contains
     * selection check box (optional)
     * play icon (depending on state)
     * song title
     * favorite/star picker
     * song duration
     * song album name
     * song artist
    """

    __gtype_name__ = "SongRow"

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    selected = GObject.Property(type=bool, default=False)

    _playlists = Playlists.get_default()

    _album_label = Gtk.Template.Child()
    _artist_label = Gtk.Template.Child()
    _duration_label = Gtk.Template.Child()
    _play_icon = Gtk.Template.Child()
    # _select_button = Gtk.Template.Child()
    _star_image = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()

    class State(IntEnum):
        """The state of the SongWidget
        """
        UNPLAYABLE = 0
        UNPLAYED = 1
        PLAYING = 2

    def __repr__(self):
        return '<SongRow>'

    def __init__(self, media):
        super().__init__()

        self._media = media
        self._selection_mode = False
        self._state = SongRow.State.UNPLAYED

        self.get_style_context().add_class('song-row')

        title = utils.get_media_title(media)
        self._title_label.props.label = title

        time = utils.seconds_to_string(media.get_duration())
        self._duration_label.props.label = time

        self._star_image.props.favorite = media.get_favourite()

        artist = utils.get_artist_name(media)
        self._artist_label.props.label = artist

        album = utils.get_album_title(media)
        self._album_label.props.label = album

        # self.bind_property(
        #     'selected', self._select_button, 'active',
        #     GObject.BindingFlags.BIDIRECTIONAL
        #     | GObject.BindingFlags.SYNC_CREATE)

    # @Gtk.Template.Callback()
    # def _on_selection_changed(self, klass, value):
    #     self.emit('selection-changed')

    @Gtk.Template.Callback()
    def _on_star_toggle(self, widget, event):
        (_, button) = event.get_button()
        if button != Gdk.BUTTON_PRIMARY:
            return False

        favorite = not self._star_image.favorite
        self._star_image.props.favorite = favorite

        # TODO: Rework and stop updating widgets from here directly.
        grilo.set_favorite(self._media, favorite)
        self._playlists.update_smart_playlist(SmartPlaylists.Favorites)

        return True

    @Gtk.Template.Callback()
    def _on_star_hover(self, widget, event):
        self._star_image.props.hover = True

    @Gtk.Template.Callback()
    def _on_star_unhover(self, widget, event):
        self._star_image.props.hover = False

    @GObject.Property(type=bool, default=False)
    def selection_mode(self):
        """Selection mode

        :returns: Selection mode
        :rtype: bool
        """
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, value):
        """Set the selection mode

        :param bool value: Selection mode
        """
        self._selection_mode = value
        self._select_button.set_visible(value)

        if not value:
            self.props.selected = False

    @GObject.Property(type=Grl.Media, flags=GObject.ParamFlags.READABLE)
    def media(self):
        return self._media

    @GObject.Property(type=int, default=0)
    def state(self):
        """State of the widget

        :returns: Widget state
        :rtype: SongWidget.State
        """
        return self._state

    @state.setter
    def state(self, value):
        """Set state of the of widget

        This influences the look of the widgets label and if there is a
        song play indicator being shown.

        :param SongWidget.State value: Widget state
        """
        self._state = value
        if value == SongRow.State.UNPLAYABLE:
            self._play_icon.props.icon_name = "dialog-error-symbolic"
        elif value == SongRow.State.PLAYING:
            self._play_icon.props.icon_name = "media-playback-start-symbolic"
        else:
            self._play_icon.props.icon_name = None
            self._play_icon.props.icon_size = 1
