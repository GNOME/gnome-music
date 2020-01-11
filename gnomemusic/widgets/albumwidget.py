# Copyright 2020 The GNOME Music developers
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

from gettext import ngettext

from gi.repository import GObject, Grl, Gtk

from gnomemusic.albumartcache import Art
from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.disclistboxwidget import DiscBox
from gnomemusic.widgets.disclistboxwidget import DiscListBox  # noqa: F401


@Gtk.Template(resource_path='/org/gnome/Music/ui/AlbumWidget.ui')
class AlbumWidget(Gtk.EventBox):
    """Album widget.

    The album widget consists of an image with the album art
    on the left and a list of songs on the right.
    """

    __gtype_name__ = 'AlbumWidget'

    _artist_label = Gtk.Template.Child()
    _composer_label = Gtk.Template.Child()
    _composer_info_label = Gtk.Template.Child()
    _cover_stack = Gtk.Template.Child()
    _disc_list_box = Gtk.Template.Child()
    _released_info_label = Gtk.Template.Child()
    _running_info_label = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()

    selection_mode = GObject.Property(type=bool, default=False)

    _duration = 0

    def __init__(self, application):
        """Initialize the AlbumWidget.

        :param GtkApplication application: The application object
        """
        super().__init__()

        self._application = application
        self._corealbum = None
        self._coremodel = self._application.props.coremodel
        self._duration_signal_id = None
        self._model_signal_id = None

        self._cover_stack.props.size = Art.Size.LARGE
        self._player = self._application.props.player

        self.bind_property(
            "selection-mode", self._disc_list_box, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self.connect("notify::selection-mode", self._on_selection_mode_changed)

    def update(self, corealbum):
        """Update the album widget.

        :param CoreAlbum album: The CoreAlbum object
        """
        if self._corealbum:
            self._corealbum.disconnect(self._duration_signal_id)
            self._corealbum.props.model.disconnect(self._model_signal_id)

        self._corealbum = corealbum

        self._cover_stack.update(self._corealbum)

        album_name = self._corealbum.props.title
        artist = self._corealbum.props.artist

        self._title_label.props.label = album_name
        self._title_label.props.tooltip_text = album_name

        self._artist_label.props.label = artist
        self._artist_label.props.tooltip_text = artist

        self._released_info_label.props.label = self._corealbum.props.year

        self._set_composer_label(corealbum)

        self._album_model = self._corealbum.props.model
        self._model_signal_id = self._album_model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._disc_list_box.bind_model(self._album_model, self._create_widget)

        self._on_duration_changed(self._corealbum, None)
        self._duration_signal_id = self._corealbum.connect(
            "notify::duration", self._on_duration_changed)

        self._album_model.items_changed(0, 0, 0)

    def _create_widget(self, disc):
        disc_box = DiscBox(disc)
        disc_box.connect('song-activated', self._song_activated)

        self._disc_list_box.bind_property(
            "selection-mode", disc_box, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        return disc_box

    def _on_model_items_changed(self, model, position, removed, added):
        n_items = model.get_n_items()
        if n_items == 1:
            discbox = self._disc_list_box.get_row_at_index(0)
            discbox.props.show_disc_label = False
        else:
            for i in range(n_items):
                discbox = self._disc_list_box.get_row_at_index(i)
                discbox.props.show_disc_label = True

    def _set_composer_label(self, corealbum):
        composer = corealbum.props.composer
        show = False

        if composer:
            self._composer_info_label.props.label = composer
            self._composer_info_label.props.max_width_chars = 10
            self._composer_info_label.props.tooltip_text = composer
            show = True

        self._composer_label.props.visible = show
        self._composer_info_label.props.visible = show

    def _on_duration_changed(self, coredisc, duration):
        mins = (coredisc.props.duration // 60) + 1
        self._running_info_label.props.label = ngettext(
            "{} minute", "{} minutes", mins).format(mins)

    def _song_activated(self, widget, song_widget):
        if self.props.selection_mode:
            song_widget.props.selected = not song_widget.props.selected
            return

        signal_id = None

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play(song_widget.props.coresong)
            self._coremodel.disconnect(signal_id)

        signal_id = self._coremodel.connect(
            "playlist-loaded", _on_playlist_loaded)
        self._coremodel.props.active_media = self._corealbum

        return True

    def select_all(self):
        self._disc_list_box.select_all()

    def deselect_all(self):
        self._disc_list_box.deselect_all()

    def _on_selection_mode_changed(self, widget, value):
        if not self.props.selection_mode:
            self.deselect_all()

    @GObject.Property(
        type=Grl.Media, default=None, flags=GObject.ParamFlags.READABLE)
    def album(self):
        """Get the current album.

        :returns: the current album
        :rtype: CoreAlbum
        """
        return self._corealbum
