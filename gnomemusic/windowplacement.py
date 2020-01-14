# Copyright 2018 The GNOME Music developers
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

from gi.repository import GLib, GObject


class WindowPlacement(GObject.GObject):
    """Main window placement

    Restores and saves the main window placement, success may vary
    depending on the underlying window manager.
    """

    __gtype_name__ = 'WindowPlacement'

    def __init__(self, window):
        """Initialize WindowPlacement

        :param Gtk.Window window: Main window
        """
        super().__init__()

        self._window = window
        application = window.props.application
        self._settings = application.props.settings

        self._restore_window_state()

        self._window_placement_update_timeout = None
        self._window.connect('notify::is-maximized', self._on_maximized)
        self._window.connect('configure-event', self._on_configure_event)

    def _restore_window_state(self):
        size_setting = self._settings.get_value('window-size')
        if (len(size_setting) == 2
                and isinstance(size_setting[0], int)
                and isinstance(size_setting[1], int)):
            self._window.resize(size_setting[0], size_setting[1])

        position_setting = self._settings.get_value('window-position')
        if (len(position_setting) == 2
                and isinstance(position_setting[0], int)
                and isinstance(position_setting[1], int)):
            self._window.move(position_setting[0], position_setting[1])

        if self._settings.get_value('window-maximized'):
            self._window.maximize()

    def _on_configure_event(self, widget, event):
        if self._window_placement_update_timeout is None:
            self._window_placement_update_timeout = GLib.timeout_add(
                500, self._store_size_and_position, widget)

    def _store_size_and_position(self, widget):
        size = widget.get_size()
        self._settings.set_value(
            'window-size', GLib.Variant('ai', [size[0], size[1]]))

        position = widget.get_position()
        self._settings.set_value(
            'window-position', GLib.Variant('ai', [position[0], position[1]]))

        GLib.source_remove(self._window_placement_update_timeout)
        self._window_placement_update_timeout = None

        return False

    def _on_maximized(self, klass, value, data=None):
        self._settings.set_boolean(
            'window-maximized', self._window.is_maximized())
