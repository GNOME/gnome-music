# Copyright 2021 The GNOME Music developers
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
from typing import List, Optional
import typing

import gi
gi.require_version("Grl", "0.3")
from gi.repository import GLib, GObject, Grl

if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coresong import CoreSong
    from gnomemusic.coregrilo import CoreGrilo
    from gnomemusic.musiclogger import MusicLogger


class GrlChromaprintWrapper(GObject.GObject):
    """Wrapper for the Grilo Chromaprint source.
    """

    def __init__(self, source: Grl.Source, application: Application) -> None:
        """Initialize the Chromaprint wrapper

        :param Grl.Source source: The Chromaprint source to wrap
        :param Application application: Application object
        """
        super().__init__()

        self._source: Grl.Source = source
        self._log: MusicLogger = application.props.log

        coregrilo: CoreGrilo = application.props.coregrilo
        registry: Grl.Registryy = coregrilo.props.registry
        self._fingerprint_key: int = registry.lookup_metadata_key(
            "chromaprint")

        self._METADATA_KEYS: List[int] = [
            self._fingerprint_key,
            Grl.METADATA_KEY_DURATION
        ]

        if not self.props.enabled:
            self._log.warning(
                "Error: chromaprint GStreamer plugin is missing.")

    def get_chromaprint(
            self, coresong: CoreSong,
            callback: CoreGrilo.RESOLVE_CB_TYPE) -> None:
        """Get the chromaprint of a coresong.

        Compute the chromaprint of a song a call
        a callback function with a Grl.Media which contains the
        chromaprint.

        :param CoreSong coresong: song to analyze
        :param function callback:  callback function
        """
        if not self.props.enabled:
            self._log.warning(
                "Error: chromaprint GStreamer plugin is missing.")
            callback(None)
            return

        chromaprint: str = coresong.props.media.get_string(
            self._fingerprint_key)
        if chromaprint:
            callback(coresong.props.media)
            return

        options: Grl.OperationOptions = Grl.OperationOptions()
        options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        def _chromaprint_resolved(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                callback: CoreGrilo.RESOLVE_CB_TYPE,
                error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning(
                    "Error {}: {}".format(error.domain, error.message))
                callback(None)
                return

            callback(media)

        self._source.resolve(
            coresong.props.media, self._METADATA_KEYS, options,
            _chromaprint_resolved, callback)

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def enabled(self) -> bool:
        """Get Chromaprint source state.

        A chromaprint can be computed if gstreamer chromaprint
        support is enabled.

        :returns: chromaprint source state
        :rtype: bool
        """
        return self._fingerprint_key != Grl.METADATA_KEY_INVALID
