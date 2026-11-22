# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008
# SPDX-FileCopyrightText: Copyright the GNOME Music authors

from gi.repository import Adw, GObject, Gtk


@Gtk.Template(resource_path="/org/gnome/Music/ui/widgets/MainHeaderBar.ui")
class MainHeaderBar(Adw.Bin):
    """Headerbar of the main view of the application."""

    __gtype_name__ = "MainHeaderBar"

    _menu_button = Gtk.Template.Child()

    search_mode_active = GObject.Property(type=bool, default=False)
    stack = GObject.Property(type=Adw.ViewStack)

    def __init__(self) -> None:
        super().__init__()

        builder = Gtk.Builder.new_from_resource(
            "/org/gnome/Music/ui/menu/PrimaryMenu.ui")
        self._menu_button.props.menu_model = builder.get_object("primary_menu")
