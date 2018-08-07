import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import sys

class ErrorDialog():
    def __init__(self,err_msg):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK, "%s not found" % (err_msg[0]))
        dialog.format_secondary_text("%s is either missing or you have version other than \'%s\'\nplease install it using \"sudo apt install %s\"" % (err_msg[0],err_msg[1],err_msg[0].lower()))
        dialog.run()
        dialog.destroy()
        sys.exit(1)
