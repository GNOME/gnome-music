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

from gettext import gettext as _
from gi.repository import GObject, Gtk

from gnomemusic import log


@Gtk.Template(resource_path="/org/gnome/Music/ui/InfoBar.ui")
class InfoBar(Gtk.InfoBar):
    """Display messages and errors in the info bar.

    Messages come in two parts: a high-level summary, and a detailed
    description.
    """
    __gtype_name__ = "InfoBar"
    _label = Gtk.Template.Child()

    def __init__(self):
        """Initialize the Info bar

        :param Gtk.Box
        """
        super().__init__()

        content = self.get_content_area()
        content.show()

    @Gtk.Template.Callback()
    @log
    def _on_ok_button_clicked(self, entry):
        self.hide()

    @log
    def set_msg(self, main, detail):
        self._label.set_markup('<b>%s</b>\n%s' % _((main, detail)))

    @log
    def error(self, main, detail):
        """Display an error message.

        :param main -- a summary of the error
        :param detail -- error details
        """
        self.set_msg(main, detail)
        self.show()
