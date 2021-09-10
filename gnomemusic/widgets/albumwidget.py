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

from __future__ import annotations
from gettext import ngettext
from typing import Optional, Union
import typing

from gi.repository import Gfm, Gio, GLib, GObject, Gtk, Handy

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.defaulticon import DefaultIcon
from gnomemusic.utils import ArtSize
from gnomemusic.widgets.disclistboxwidget import DiscBox
from gnomemusic.widgets.playlistdialog import PlaylistDialog
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coreartist import CoreArtist
    from gnomemusic.coredisc import CoreDisc
    from gnomemusic.coresong import CoreSong
    from gnomemusic.widgets.songwidget import SongWidget


@Gtk.Template(resource_path='/org/gnome/Music/ui/AlbumWidget.ui')
class AlbumWidget(Handy.Clamp):
    """Album widget.

    The album widget consists of an image with the album art
    on the left and a list of songs on the right.
    """

    __gtype_name__ = 'AlbumWidget'

    _artist_label = Gtk.Template.Child()
    _composer_label = Gtk.Template.Child()
    _art_stack = Gtk.Template.Child()
    _disc_list_box = Gtk.Template.Child()
    _menu_button = Gtk.Template.Child()
    _play_button = Gtk.Template.Child()
    _released_label = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()

    selection_mode = GObject.Property(type=bool, default=False)
    show_artist_label = GObject.Property(type=bool, default=True)

    def __init__(self, application: Application) -> None:
        """Initialize the AlbumWidget.

        :param GtkApplication application: The application object
        """
        super().__init__()

        self._album_model = None
        self._application = application
        self._corealbum: CoreAlbum
        self._active_coreobject: Union[CoreAlbum, CoreArtist]
        self._coremodel = self._application.props.coremodel
        self._duration_signal_id = 0
        self._year_signal_id = 0
        self._model_signal_id = 0

        self._art_stack.props.size = ArtSize.LARGE
        self._art_stack.props.art_type = DefaultIcon.Type.ALBUM
        self._player = self._application.props.player

        self.bind_property(
            "selection-mode", self._disc_list_box, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self.bind_property(
            "show-artist-label", self._artist_label, "visible",
            GObject.BindingFlags.SYNC_CREATE)

        self.connect("notify::selection-mode", self._on_selection_mode_changed)

        action_group = Gio.SimpleActionGroup()
        actions = (
            ("play", self._on_play_action),
            ("add_favorites", self._on_add_favorites_action),
            ("add_playlist", self._on_add_playlist_action)
        )
        for (name, callback) in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            action_group.add_action(action)

        self.insert_action_group("album", action_group)

    @GObject.Property(
        type=CoreAlbum, default=None, flags=GObject.ParamFlags.READWRITE)
    def corealbum(self) -> Optional[CoreAlbum]:
        """Get the current CoreAlbum.

        :returns: The current CoreAlbum
        :rtype: CoreAlbum or None
        """
        try:
            return self._corealbum
        except AttributeError:
            return None

    @corealbum.setter  # type:ignore
    def corealbum(self, corealbum: CoreAlbum) -> None:
        """Update CoreAlbum used for AlbumWidget.

        :param CoreAlbum corealbum: The CoreAlbum object
        """
        if (self._duration_signal_id != 0
                or self._year_signal_id != 0
                or self._model_signal_id != 0):
            self._corealbum.disconnect(self._duration_signal_id)
            self._corealbum.disconnect(self._year_signal_id)
            self._corealbum.props.model.disconnect(self._model_signal_id)

        self._corealbum = corealbum

        self._art_stack.props.coreobject = self._corealbum

        album_name = self._corealbum.props.title
        artist = self._corealbum.props.artist

        self._title_label.props.label = album_name
        self._title_label.props.tooltip_text = album_name

        self._artist_label.props.label = artist
        self._artist_label.props.tooltip_text = artist

        self._duration_signal_id = self._corealbum.connect(
            "notify::duration", self._on_release_info_changed)
        self._year_signal_id = self._corealbum.connect(
            "notify::year", self._on_release_info_changed)
        self._set_composer_label()

        self._album_model = self._corealbum.props.model
        self._model_signal_id = self._album_model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._disc_list_box.bind_model(self._album_model, self._create_widget)

        self._album_model.items_changed(0, 0, 0)

    @GObject.Property(
        type=object, default=None, flags=GObject.ParamFlags.READWRITE)
    def active_coreobject(self) -> Optional[Union[CoreAlbum, CoreArtist]]:
        """Get the current CoreObject.

        active_coreobject is used to set the Player playlist
        AlbumWidget can be used to display an Album in AlbumsView or
        ArtistsView. In the former case, there is no need to set it: it's
        already the corealbum. In the later case, the active_coreobject is
        an artist. It needs to be set.

        :returns: The current CoreObject
        :rtype: Union[CoreAlbum, CoreArtist]
        """
        try:
            return self._active_coreobject
        except AttributeError:
            return self.props.corealbum

    @active_coreobject.setter  # type:ignore
    def active_coreobject(
            self, coreobject: Union[CoreAlbum, CoreArtist]) -> None:
        """Update CoreOject used for AlbumWidget.

        :param CoreAlbum corealbum: The CoreAlbum object
        """
        self._active_coreobject = coreobject

    def _create_widget(self, disc: CoreDisc) -> DiscBox:
        disc_box = DiscBox(self._application, self._corealbum, disc)
        disc_box.connect('song-activated', self._song_activated)

        self._corealbum.bind_property(
            "selected", disc, "selected", GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", disc_box, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        return disc_box

    def _on_model_items_changed(
            self, model: Gfm.SortListModel, position: int, removed: int,
            added: int) -> None:
        n_items: int = model.get_n_items()
        if n_items == 1:
            discbox = self._disc_list_box.get_row_at_index(0)
            discbox.props.show_disc_label = False
        else:
            for i in range(n_items):
                discbox = self._disc_list_box.get_row_at_index(i)
                discbox.props.show_disc_label = True

        empty_album = (n_items == 0)
        self._play_button.props.sensitive = not empty_album
        self._menu_button.props.sensitive = not empty_album

    def _set_composer_label(self) -> None:
        composer = self._corealbum.props.composer
        show = False

        if composer:
            self._composer_label.props.label = composer
            self._composer_label.props.tooltip_text = composer
            show = True

        self._composer_label.props.visible = show
        self._composer_label.props.visible = show

    def _on_release_info_changed(
            self, klass: CoreAlbum,
            value: Optional[GObject.ParamSpecString]) -> None:
        if not self._corealbum:
            return

        mins = (self._corealbum.props.duration // 60) + 1
        mins_text = ngettext("{} minute", "{} minutes", mins).format(mins)
        year = self._corealbum.props.year

        if year == "----":
            label = mins_text
        else:
            label = f"{year}, {mins_text}"

        self._released_label.props.label = label

    def _play(self, coresong: Optional[CoreSong] = None) -> None:
        signal_id = 0

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play(coresong)
            self._coremodel.disconnect(signal_id)

        signal_id = self._coremodel.connect(
            "playlist-loaded", _on_playlist_loaded)
        self._coremodel.props.active_core_object = self.props.active_coreobject

    def _song_activated(
            self, widget: Gtk.Widget, song_widget: SongWidget) -> None:
        if self.props.selection_mode:
            song_widget.props.selected = not song_widget.props.selected
            return

        self._play(song_widget.props.coresong)

    def select_all(self) -> None:
        if self._album_model:
            for coredisc in self._album_model:
                coredisc.props.selected = True

    def deselect_all(self) -> None:
        if self._album_model:
            for coredisc in self._album_model:
                coredisc.props.selected = False

    def _on_selection_mode_changed(
            self, widget: Gtk.Widget, value: GObject.ParamSpecBoolean) -> None:
        if not self.props.selection_mode:
            self.deselect_all()

    def _on_add_favorites_action(
            self, action: Gio.SimpleAction,
            data: Optional[GLib.Variant]) -> None:
        if self._corealbum:
            for coredisc in self._corealbum.props.model:
                for coresong in coredisc.props.model:
                    if not coresong.props.favorite:
                        coresong.props.favorite = True

    def _on_add_playlist_action(
            self, action: Gio.SimpleAction,
            data: Optional[GLib.Variant]) -> None:
        if not self._corealbum:
            return

        playlist_dialog = PlaylistDialog(self._application)
        active_window = self._application.props.active_window
        playlist_dialog.props.transient_for = active_window
        if playlist_dialog.run() == Gtk.ResponseType.ACCEPT:
            playlist = playlist_dialog.props.selected_playlist
            coresongs = [
                song
                for disc in self._corealbum.props.model
                for song in disc.props.model]
            playlist.add_songs(coresongs)

        playlist_dialog.destroy()

    def _on_play_action(
            self, action: Gio.SimpleAction,
            data: Optional[GLib.Variant]) -> None:
        self._play()

    @Gtk.Template.Callback()
    def _on_play_button_clicked(self, button: Gtk.Button) -> None:
        # When the coreobject is an artist, the first song of the album
        # needs to be loaded. Otherwise, the first album of the artist
        # is played.
        coresong: Optional[CoreSong] = None
        if self.props.active_coreobject != self.props.corealbum:
            coredisc = self.props.corealbum.props.model[0]
            coresong = coredisc.props.model[0]

        self._play(coresong)
