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
from typing import Optional
import typing

from gettext import gettext as _
from gi.repository import Adw, GLib, GObject, Gio, Gtk
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.grilowrappers.playlist import Playlist


class PlaylistToast(GObject.Object):
    """Toast for playlist deletion, including undo
    """

    __gtype_name__ = "PlaylistToast"

    def __init__(self, application: Application, playlist: Playlist) -> None:
        """Initialize the toast for song deletion

        :param Application application: Application object
        :param Playlist playlist: The playlist that contains the song
        """
        super().__init__()

        self._coregrilo = application.props.coregrilo
        self._playlist = playlist
        self._undo = False

        toast = Adw.Toast.new(
            _("Playlist {} removed".format(self._playlist.props.title)))
        toast.set_button_label(_("Undo"))

        toast.set_action_name("toast.undo")
        application.props.window.install_action(
            "toast.undo", None, self._toast_undo_cb)

        toast.connect("dismissed", self._on_dismissed)
        self._coregrilo.stage_playlist_deletion(self._playlist)

        application.props.window._toast_overlay.add_toast(toast)

    def _toast_undo_cb(
            self, widget: Gtk.Widget, action: Gio.Action,
            param: Optional[GLib.Variant]) -> None:
        self._undo = True
        self._coregrilo.finish_playlist_deletion(self._playlist, False)

    def _on_dismissed(self, widget: Gtk.Widget) -> None:
        if not self._undo:
            self._coregrilo.finish_playlist_deletion(self._playlist, True)
