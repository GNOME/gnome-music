# Copyright (c) 2018 The GNOME Music Developers
#
# GNOME Music is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# GNOME Music is distributed in the hope that it will be useful,
# but WITHOUT AcexloNY WARRANTY; without even the implied warranty of
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

import sys

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk


class ErrorDialog(Gtk.Dialog):
	"""Dialog for missing dependency error"""
	
	def set_error_msg(self, err_msg):
		"""Set error message for the error dialog"""
		
		return """\'%s\' is either missing or you have version other than \'%s\'
		please install %s be""".replace('\n\t\t', ' ').strip() % (
			err_msg[0].lower(), 
			err_msg[1], 
			err_msg[0].lower()
		)
	
	def __repr__(self):
		return '<ErrorDialog>'

	def __init__(self, err_msg):
		Gtk.Dialog.__init__(self, "%s not found" % (err_msg[0]), 
							None, 0, (Gtk.STOCK_OK, Gtk.ResponseType.OK))
							
		self.set_default_size(50,100)
		msg = Gtk.Label(self.set_error_msg(err_msg))
		self.get_content_area().add(msg)
		
		self.show_all()
		
		if self.run():
			sys.exit(1)
        
