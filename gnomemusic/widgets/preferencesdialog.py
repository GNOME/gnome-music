# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
import typing

from gi.repository import GObject, Gio, Gtk, Adw

if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path='/org/gnome/Music/ui/PreferencesDialog.ui')
class PreferencesDialog(Adw.PreferencesDialog):
    """Main menu preferences dialog
    """

    __gtype_name__ = "PreferencesDialog"

    _inhibit_suspend_row = Gtk.Template.Child()
    _repeatmode_row = Gtk.Template.Child()
    _replay_gain_row = Gtk.Template.Child()

    def __init__(self, application: Application) -> None:
        """Initialize the application settings dialog.

        :param Application application: Application object
        """
        super().__init__()

        self._settings = application.props.settings

        self._repeatmode_row.props.selected = self._settings.get_enum("repeat")
        self._repeatmode_row.connect(
            "notify::selected", self._update_repeate_mode)

        self._replay_gain_row.props.selected = self._settings.get_enum(
            "replaygain")
        self._replay_gain_row.connect(
            "notify::selected", self._update_replaygain)

        self._settings.bind(
            "inhibit-suspend", self._inhibit_suspend_row, "active",
            Gio.SettingsBindFlags.DEFAULT)

    def _update_repeate_mode(
            self, row: Adw.ComboRow, value: GObject.ParamSpecInt) -> None:
        self._settings.set_enum("repeat", row.props.selected)

    def _update_replaygain(
            self, row: Adw.ComboRow, value: GObject.ParamSpecInt) -> None:
        self._settings.set_enum("replaygain", row.props.selected)
