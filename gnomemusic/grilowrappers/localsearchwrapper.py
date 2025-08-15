# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Callable, Dict, List, Optional
import typing

import gi
gi.require_versions({"Tracker": "3.0"})
from gi.repository import Grl, Gio, Gtk, GLib, GObject, Tracker

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coredisc import CoreDisc
from gnomemusic.coresong import CoreSong
from gnomemusic.grilowrappers.grltrackerplaylists import (
    GrlTrackerPlaylists, Playlist)
from gnomemusic.storeart import StoreArt
from gnomemusic.trackerwrapper import TrackerWrapper
from gnomemusic.utils import CoreObjectType
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coremodel import CoreModel
    from gnomemusic.musiclogger import MusicLogger
    from gnomemusic.notificationmanager import NotificationManager


class LocalSearchWrapper(GObject.Object):

    __gtype_name__ = "LocalSearchWrapper"

    def __init__(
        self, application: Application,
        localsearchwrapper: TrackerWrapper) -> None:
        """
        """
        super().__init__()

        self._application = application
        self._log = application.props.log

        self._albums_model = Gio.ListStore.new(CoreAlbum)

        cm = application.props.coremodel
        cm.albums_proxy.append(self._albums_model)

        self._init_albums_model()

    def _init_albums_model(self) -> None:
        pass
