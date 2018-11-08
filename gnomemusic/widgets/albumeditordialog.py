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
from gi.repository import Gdk, GdkPixbuf, GObject, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art, make_icon_frame
import gnomemusic.utils as utils


@Gtk.Template(resource_path='/org/gnome/Music/ui/AlbumEditorDialog.ui')
class AlbumEditorDialog(Gtk.Dialog):

    __gtype_name__ = 'AlbumEditorDialog'

    _album_entry = Gtk.Template.Child()
    _artist_entry = Gtk.Template.Child()
    _cover_stack = Gtk.Template.Child()
    _genre_entry = Gtk.Template.Child()
    _select_button = Gtk.Template.Child()
    _title_bar = Gtk.Template.Child()
    _year_entry = Gtk.Template.Child()

    _detail_fields = ['album', 'artist', 'genre', 'year']

    new_cover = GObject.Property(type=str, default=None)

    def __repr__(self):
        return '<AlbumEditorDialog>'

    @log
    def __init__(self, parent, album):
        super().__init__()

        self._album = album
        self._parent = parent
        self.props.transient_for = self._parent
        self.set_titlebar(self._title_bar)

        self._scale = self._parent.get_scale_factor()
        self._size = Art.Size.LARGE
        self._cover_stack.props.size = self._size
        self._cover_stack.update(album)

        self._init_labels()

    @log
    def _init_labels(self):
        for field in self._detail_fields:
            entry = getattr(self, '_' + field + '_entry')
            value = utils.fields[field](self._album)
            if value:
                entry.props.text = value

    @Gtk.Template.Callback()
    @log
    def _on_selection(self, select_button):
        self.response(Gtk.ResponseType.ACCEPT)

    @Gtk.Template.Callback()
    @log
    def _on_cancel_button_clicked(self, cancel_button):
        self.response(Gtk.ResponseType.REJECT)

    @Gtk.Template.Callback()
    @log
    def _choose_cover(self, btn):
        dialog_title = _("Choose album cover")
        chooser_dialog = Gtk.FileChooserDialog(
            dialog_title, self._parent, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        image_filter = Gtk.FileFilter()
        image_filter.set_name(_("Image"))
        image_filter.add_mime_type("image/png")
        image_filter.add_mime_type("image/jpeg")
        chooser_dialog.add_filter(image_filter)

        response = chooser_dialog.run()
        if response == Gtk.ResponseType.OK:
            new_filename = chooser_dialog.get_filename()
            preview_pixbuf = GdkPixbuf.Pixbuf.new_from_file(new_filename)
            surface = Gdk.cairo_surface_create_from_pixbuf(
                preview_pixbuf, self._scale, None)
            surface = make_icon_frame(surface, self._size, self._scale)
            self._cover_stack.update_from_surface(surface)
            self.props.new_cover = new_filename
            self._select_button.props.sensitive = True

        chooser_dialog.destroy()
