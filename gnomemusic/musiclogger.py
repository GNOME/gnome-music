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
import os

from gi.repository import GLib, GObject


class MusicLogger(GObject.GObject):
    """GLib logging wrapper

    A tiny wrapper around the default GLib logger.

    * Message is for user facing warnings, which ideally should be in
      the application.
    * Warning is for logging non-fatal errors during execution.
    * Debug is for developer use as a way to get more runtime info.
    """

    _DOMAIN = "org.gnome.Music"

    def _log(self, message, level):
        stack = inspect.stack()

        filename = os.path.basename(stack[2][1])
        line = stack[2][2]
        function = stack[2][3]

        if level in [GLib.LogLevelFlags.LEVEL_DEBUG,
                     GLib.LogLevelFlags.LEVEL_INFO,
                     GLib.LogLevelFlags.LEVEL_WARNING]:
            message = "({}, {}, {}) {}".format(
                filename, function, line, message)

        variant_message = GLib.Variant("s", message)
        variant_file = GLib.Variant("s", filename)
        variant_line = GLib.Variant("i", line)
        variant_func = GLib.Variant("s", function)

        variant_dict = GLib.Variant("a{sv}", {
            "MESSAGE": variant_message,
            "CODE_FILE": variant_file,
            "CODE_LINE": variant_line,
            "CODE_FUNC": variant_func
        })

        GLib.log_variant(self._DOMAIN, level, variant_dict)

    def message(self, message):
        """The default user facing message

        Wraps g_message.

        :param string message: Message
        """
        self._log(message, GLib.LogLevelFlags.LEVEL_MESSAGE)

    def warning(self, message):
        """Warning message

        Wraps g_warning.

        :param string message: Warning message
        """
        self._log(message, GLib.LogLevelFlags.LEVEL_WARNING)

    def info(self, message):
        """Informational message

        Wraps g_info.

        :param string message: Informational message
        """
        self._log(message, GLib.LogLevelFlags.LEVEL_INFO)

    def debug(self, message):
        """Debug message

        Wraps g_debug.

        :param string message: Debug message
        """
        self._log(message, GLib.LogLevelFlags.LEVEL_DEBUG)
