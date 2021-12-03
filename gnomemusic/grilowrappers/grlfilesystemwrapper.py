# Copyright 2022 The GNOME Music developers
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

from gi.repository import Gio, GLib, GObject, Grl

from gnomemusic.coresong import CoreSong
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


class GrlFileSystemWrapper(GObject.GObject):
    """Wrapper for the Grilo FileSystem source.
    """

    METADATA_KEYS = [
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_URL
    ]

    def __init__(self, source: Grl.Source, application: Application) -> None:
        """Initialize the FileSystem wrapper

        :param Grl.Source source: The Grilo source to wrap
        :param Application application: Application instance
        """
        super().__init__()

        self._application = application
        self._coreselection = application.props.coreselection
        self._log = application.props.log
        self._source = source

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        coremodel = application.props.coremodel
        self._files_model = coremodel.props.files

    def load_file(self, file: Gio.File) -> None:
        """Load an audio file

        :param Grl.Media media: The directory to browse
        """
        def resolve_cb(
                source: Grl.Source, op_id: int,
                resolved_media: Optional[Grl.Media],
                error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            if (not resolved_media
                    or not resolved_media.is_audio()):
                return

            coresong = CoreSong(self._application, resolved_media)
            self._files_model.append(coresong)

        # filesystem resolve operation does not check the mime type and
        # accepts any valid uri.
        # This step ensures that "file" is a valid audio file.
        try:
            info = file.query_info(
                Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE,
                Gio.FileQueryInfoFlags.NONE)
        except GLib.GError as error:
            self._log.warning(f"Error: {error.message}")
            return

        content_type = info.get_content_type()
        if (not content_type
                or not content_type.startswith("audio")):
            self._log.warning(f"{file.get_uri()} is not a valid audio file.")
            return

        media = Grl.Media.audio_new()
        media.set_id(file.get_uri())
        self._source.resolve(
            media, self.METADATA_KEYS, self._fast_options, resolve_cb)
