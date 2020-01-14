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

import inspect

from gi.repository import GObject, GLib


class MusicLogger(GObject.GObject):
    """GLib logging wrapper

    A tiny wrapper aroung the default GLib logger.
    """

    _DOMAIN = "org.gnome.Music"

    def _log(self, message, level):
        variant_message = GLib.Variant("s", message)
        stack = inspect.stack()
        variant_file = GLib.Variant("s", stack[2][1])
        variant_line = GLib.Variant("i", stack[2][2])
        variant_func = GLib.Variant("s", stack[2][3])

        variant_dict = GLib.Variant("a{sv}", {
            "MESSAGE": variant_message,
            "CODE_FILE": variant_file,
            "CODE_LINE": variant_line,
            "CODE_FUNC": variant_func
        })

        GLib.log_variant(self._DOMAIN, level, variant_dict)

    def message(self, message):
        self._log(message, GLib.LogLevelFlags.LEVEL_MESSAGE)

    def warning(self, message):
        self._log(message, GLib.LogLevelFlags.LEVEL_WARNING)

    def info(self, message):
        self._log(message, GLib.LogLevelFlags.LEVEL_INFO)

    def debug(self, message):
        self._log(message, GLib.LogLevelFlags.LEVEL_DEBUG)
