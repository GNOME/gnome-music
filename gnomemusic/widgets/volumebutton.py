# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations

from gi.repository import GLib, GObject, GstAudio, Gtk


@Gtk.Template(resource_path="/org/gnome/Music/ui/VolumeButton.ui")
class VolumeButton(Gtk.Box):
    """Volume button widget with a mute button and a slider."""

    __gtype_name__ = "VolumeButton"

    _adjustment = Gtk.Template.Child()
    _menu_button = Gtk.Template.Child()
    _mute_button = Gtk.Template.Child()

    mute = GObject.Property(type=bool, default=False)
    volume = GObject.Property(type=float, default=1.0)

    def __init__(self) -> None:
        """Initialize the volume button.
        """
        super().__init__()

        self.bind_property(
            "mute", self._mute_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._adjustment_id = self._adjustment.connect(
            "value-changed", self._on_adjustment_changed)
        self._mute_id = self.connect(
            "notify::mute", self._on_mute_changed)
        self._volume_id = self.connect(
            "notify::volume", self._on_volume_changed)

    def _on_adjustment_changed(self, adjustment: Gtk.Adjustment) -> None:
        with GObject.signal_handler_block(self, self._volume_id):
            self.props.volume = self._cubic_to_linear(adjustment.props.value)

        if self.props.volume == 0:
            self.props.mute = True
        elif self.props.mute:
            self.props.mute = False

        GLib.idle_add(self._update_icon)

    def _on_mute_changed(
            self, widget: VolumeButton, pspec: GObject.ParamSpec) -> None:
        if (not self.props.mute
                and self.props.volume == 0):
            with GObject.signal_handler_block(self, self._volume_id):
                self.props.volume = self._cubic_to_linear(0.25)

        GLib.idle_add(self._set_adjustment)
        GLib.idle_add(self._update_icon)

    def _on_volume_changed(
            self, widget: VolumeButton, pspec: GObject.ParamSpec) -> None:
        if (not self.props.mute
                and self.props.volume == 0):
            with GObject.signal_handler_block(self, self._mute_id):
                self.props.mute = True

        GLib.idle_add(self._set_adjustment)

    def _cubic_to_linear(self, value: float) -> float:
        return GstAudio.stream_volume_convert_volume(
            GstAudio.StreamVolumeFormat.CUBIC,
            GstAudio.StreamVolumeFormat.LINEAR,
            value
        )

    def _linear_to_cubic(self, value: float) -> float:
        return GstAudio.stream_volume_convert_volume(
            GstAudio.StreamVolumeFormat.LINEAR,
            GstAudio.StreamVolumeFormat.CUBIC,
            value
        )

    def _set_adjustment(self) -> bool:
        volume = self.props.volume
        if self.props.mute:
            value = 0.
        else:
            value = self._linear_to_cubic(volume)

        with GObject.signal_handler_block(
                self._adjustment, self._adjustment_id):
            self._adjustment.props.value = value

        return GLib.SOURCE_REMOVE

    def _update_icon(self) -> None:
        volume_cubic = self._linear_to_cubic(self.props.volume)

        if self.props.mute:
            icon_name = "audio-volume-muted-symbolic"
        elif volume_cubic < 0.3:
            icon_name = "audio-volume-low-symbolic"
        elif volume_cubic < 0.7:
            icon_name = "audio-volume-medium-symbolic"
        else:
            icon_name = "audio-volume-high-symbolic"

        self._menu_button.props.icon_name = icon_name
