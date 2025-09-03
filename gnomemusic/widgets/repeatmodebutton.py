# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Optional

from gi.repository import Gio, GLib, GObject, Gtk

from gnomemusic.player import Player, RepeatMode


@Gtk.Template(resource_path="/org/gnome/Music/ui/RepeatModeButton.ui")
class RepeatModeButton(Gtk.Box):
    """Repeat mode button widget."""

    __gtype_name__ = "RepeatModeButton"

    _menu_button = Gtk.Template.Child()

    def __init__(self) -> None:
        """Initialize the repeat mode button.
        """
        super().__init__()
        self._player: Optional[Player] = None

        menu = Gio.Menu.new()
        for mode in RepeatMode:
            item = Gio.MenuItem.new()
            item.set_label(mode.label)
            item.set_action_and_target_value(
                "repeatmenu.repeat", GLib.Variant("s", str(mode.value)))
            menu.append_item(item)

        self._menu_button.props.menu_model = menu

        self._repeat_action: Gio.SimpleAction = Gio.SimpleAction.new_stateful(
            "repeat", GLib.VariantType.new("s"), GLib.Variant("s", "0"))
        action_group = Gio.SimpleActionGroup()
        action_group.add_action(self._repeat_action)
        self.insert_action_group("repeatmenu", action_group)

        self._repeat_action.connect("activate", self._on_repeat_menu_changed)

    @GObject.Property(type=Player)
    def player(self) -> Optional[Player]:
        """Player object getter

        :returns: the Player object.
        :rtype: Player
        """
        return self._player

    @player.setter  # type: ignore
    def player(self, player: Player) -> None:
        """Player object setter

        :param Player player: the Player object
        """
        self._player = player

        self._player.bind_property(
            "repeat-mode", self._menu_button, "icon-name",
            GObject.BindingFlags.DEFAULT
            | GObject.BindingFlags.SYNC_CREATE,
            lambda binding, value: value.icon,
            None)

        repeat_mode = self._player.props.repeat_mode
        self._repeat_action.set_state(
            GLib.Variant("s", str(repeat_mode.value)))

        self._player.bind_property(
            "repeat-mode", self._repeat_action, "state",
            GObject.BindingFlags.DEFAULT
            | GObject.BindingFlags.SYNC_CREATE,
            lambda binding, value: GLib.Variant("s", str(value.value)),
            None)

    def _on_repeat_menu_changed(
            self, action: Gio.SimpleAction, new_state: GLib.Variant) -> None:
        if self._player is None:
            return

        self._repeat_action.set_state(new_state)
        new_mode = RepeatMode(int(new_state.get_string()))
        self._player.props.repeat_mode = new_mode
