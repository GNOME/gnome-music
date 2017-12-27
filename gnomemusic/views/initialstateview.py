# Copyright (c) 2016 The GNOME Music Developers
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

from gnomemusic import log
from gnomemusic.albumartcache import ArtSize
from gnomemusic.views.emptyview import EmptyView


class InitialStateView(EmptyView):

    def __repr__(self):
        return '<InitialStateView>'

    @log
    def __init__(self, window, player):
        super().__init__(window, player)

        # Update image
        icon = self.builder.get_object('icon')
        icon.set_margin_bottom(32)
        icon.set_opacity(1)
        icon.set_from_resource('/org/gnome/Music/initial-state.png')
        icon.set_size_request(ArtSize.LARGE.width, ArtSize.LARGE.height)

        # Update label
        label = self.builder.get_object('label')
        label.set_label(_("Hey DJ"))
        label.set_opacity(1)
        label.set_margin_bottom(18)
