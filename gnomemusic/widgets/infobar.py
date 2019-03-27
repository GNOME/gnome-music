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


class InfoBar(Gtk.InfoBar):
    """Display messages and errors in the info bar.

    Messages come in two parts: a high-level summary, and a detailed
    description.
    """
    message_type = GObject.Property(
        type=Gtk.MessageType, default=Gtk.MessageType.INFO)

    def __init__(self, vbox):
        """Initialize the Info bar

        :param Gtk.Box
        """
        super().__init__()

        self._label = Gtk.Label("")
        content = self.get_content_area()
        content.add(self._label)
        self.add_button("OK", Gtk.ResponseType.OK)
        vbox.pack_start(self, False, False, 0)

        self._label.show()
        content.show()
        self.connect('response', self._on_hide)

    @log
    def _on_hide(self, widget, client):
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
        self.props.message_type = Gtk.MessageType.ERROR
        self.set_msg(main, detail)
        self.set_message_type(self.props.message_type)
        self.show()
