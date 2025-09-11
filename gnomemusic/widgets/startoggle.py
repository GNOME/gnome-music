# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from gettext import gettext as _
from gi.repository import Gtk


class StarToggle(Gtk.ToggleButton):
    """GtkToggleButton for marking elements as favorite

    Shows an animation when toggled.
    """

    __gtype_name__ = "StarToggle"

    def __init__(self) -> None:
        super().__init__()

        self.add_css_class("star")
        self.add_css_class("flat")
        self.add_css_class("circular")

        self.connect("toggled", self._update)
        self.connect("clicked", self._on_clicked)

        self._update(self)

    def _update(self, _widget: Gtk.ToggleButton) -> None:
        """Update the widget depending on the state."""
        starred: bool = self.props.active
        self.props.icon_name = (
            "starred-symbolic" if starred else "non-starred-symbolic")

        if starred:
            # TRANSLATORS: A verb, to unmark a song as favorite
            self.props.tooltip_text = _("Unstar")
            self.add_css_class("starred")
        else:
            # TRANSLATORS: A verb, to mark a song as favorite
            self.props.tooltip_text = _("Star")
            self.remove_css_class("starred")

    def _on_clicked(self, _widget: Gtk.ToggleButton) -> None:
        self.add_css_class("interacted")
