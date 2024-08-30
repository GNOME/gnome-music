# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Optional
import asyncio
import os
import typing

from gi.repository import GLib, Gio, GObject

from gnomemusic.gstplayer import Playback
from gnomemusic.musiclogger import MusicLogger

if typing.TYPE_CHECKING:
    from gnomemusic.player import Player


class PauseOnSuspend(GObject.GObject):
    """PauseOnSuspend object

    Contains logic to pause music on system suspend
    and inhibit suspend before pause.
    """

    def __init__(self, player: Player) -> None:
        """Initialize pause on supend handling

        :param Player player: Player object
        """
        super().__init__()

        self._log = MusicLogger()

        self._player = player

        self._conn_signal_id: int
        self._file_descriptor: int = -1
        self._suspend_proxy: Optional[Gio.DBusProxy] = None
        self._previous_state: Playback = self._player.props.state
        self._player.connect("notify::state", self._on_player_state_changed)

        asyncio.create_task(self._init_pause_on_suspend())

    async def _init_pause_on_suspend(self) -> None:
        try:
            self._suspend_proxy = await Gio.DBusProxy.new_for_bus(
                Gio.BusType.SYSTEM,
                Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
                None,
                "org.freedesktop.login1",
                "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager")
        except GLib.Error as error:
            self._log.warning(
                f"Error: Failed to contact logind daemon: {error.message}")

    def _on_player_state_changed(self, player: Player, state: int) -> None:
        if not self._suspend_proxy:
            return

        new_state = self._player.props.state
        if self._previous_state == new_state:
            return

        if (new_state == Playback.PLAYING
                and self._file_descriptor == -1):
            asyncio.create_task(self._take_lock())

        if (self._previous_state == Playback.PLAYING
                and new_state != Playback.LOADING):
            self._release_lock()

        self._previous_state = new_state

    async def _take_lock(self) -> None:
        if not self._suspend_proxy:
            return

        variant = GLib.Variant(
            "(ssss)",
            (
                "sleep",
                "GNOME Music",
                "GNOME Music is pausing",
                "delay"
            )
        )

        try:
            var = await self._suspend_proxy.call_with_unix_fd_list(
                "Inhibit", variant, Gio.DBusCallFlags.NONE, -1)
            self._file_descriptor = var.out_fd_list.get(0)
            self._conn_signal_id = self._suspend_proxy.connect(
                "g-signal", self._pause_playing)
        except GLib.Error as error:
            self._log.warning(
                f"Error: Failed to finish proxy call: {error.message}")

    def _release_lock(self) -> None:
        if not self._suspend_proxy:
            return

        if self._file_descriptor >= 0:
            os.close(self._file_descriptor)
            self._file_descriptor = -1
            self._suspend_proxy.disconnect(self._conn_signal_id)

    def _pause_playing(
            self, proxy: Gio.DBusProxy, sender: Optional[str], signal: str,
            parameters: GLib.Variant) -> None:
        if signal != "PrepareForSleep":
            return

        (going_to_sleep, ) = parameters
        if going_to_sleep is True:
            self._player.pause()
            self._release_lock()
        else:
            asyncio.create_task(self._take_lock())
