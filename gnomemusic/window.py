from gi.repository import Gtk, Gio, GLib, Tracker
from gettext import gettext as _

from gnomemusic.toolbar import Toolbar, ToolbarState
from gnomemusic.player import Player, SelectionToolbar
from gnomemusic.query import Query
import gnomemusic.view as Views

tracker = Tracker.SparqlConnection.get(None)


class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title=_('Music'))
        settings = Gio.Settings.new('org.gnome.Music')
        self.add_action(settings.create_action('repeat'))
        self.set_size_request(887, 640)
        self._setup_view()
        self.proxy = Gio.DBusProxy.new_sync(Gio.bus_get_sync(Gio.BusType.SESSION, None),
                                            Gio.DBusProxyFlags.NONE,
                                            None,
                                            'org.gnome.SettingsDaemon',
                                            '/org/gnome/SettingsDaemon/MediaKeys',
                                            'org.gnome.SettingsDaemon.MediaKeys',
                                            None)
        self.proxy.call_sync('GrabMediaPlayerKeys',
                             GLib.Variant('(su)', ('Music', 0)),
                             Gio.DBusCallFlags.NONE,
                             -1,
                             None)
        self.proxy.connect('g-signal', self._handle_media_keys)

    def _windows_focus_cb(self, window, event):
        self.proxy.call_sync('GrabMediaPlayerKeys',
                             GLib.Variant('(su)', ('Music', 0)),
                             Gio.DBusCallFlags.NONE,
                             -1,
                             None)

    def _handle_media_keys(self, proxy, sender, signal, parameters):
        if signal != 'MediaPlayerKeyPressed':
            print('Received an unexpected signal \'%s\' from media player'.format(signal))
            return
        response = parameters.get_child_value(1).get_string()
        if 'Play' in response:
            self.player.PlayPause()
        elif 'Stop' in response:
            self.player.Stop()
        elif 'Next' in response:
            self.player.Next()
        elif 'Previous' in response:
            self.player.Previous()

    def _setup_view(self):
        self._box = Gtk.VBox()
        self.player = Player()
        self.selection_toolbar = SelectionToolbar()
        self.toolbar = Toolbar()
        self.set_titlebar(self.toolbar.header_bar)
        self.views = []
        self._stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=100,
            visible=True)
        self._box.pack_start(self._stack, True, True, 0)
        self._box.pack_start(self.player.eventBox, False, False, 0)
        self._box.pack_start(self.selection_toolbar.eventbox, False, False, 0)
        self.add(self._box)
        count = 1
        cursor = tracker.query(Query.SONGS_COUNT, None)
        if cursor is not None and cursor.next(None):
            count = cursor.get_integer(0)
        if count > 0:
            self.views.append(Views.Albums(self.toolbar, self.selection_toolbar, self.player))
            self.views.append(Views.Artists(self.toolbar, self.selection_toolbar, self.player))
            self.views.append(Views.Songs(self.toolbar, self.selection_toolbar, self.player))
            #self.views.append(Views.Playlist(self.toolbar, self.selection_toolbar, self.player))

            for i in self.views:
                self._stack.add_titled(i, i.title, i.title)

            self.toolbar.set_stack(self._stack)

            self._on_notify_model_id = self._stack.connect("notify::visible-child", self._on_notify_mode)
            self.connect("destroy", self._notify_mode_disconnect)

            self.views[0].populate()
        #To revert to the No Music View when no songs are found
        else:
            self.views[0] = Views.Empty(self.toolbar, self.player)
            self._stack.add_titled(self.views[0], "Empty", "Empty")

        self.toolbar.set_state(ToolbarState.ALBUMS)
        self.toolbar.header_bar.show()
        self.player.eventBox.show_all()
        self._box.show()
        self.show()

    def _notify_mode_disconnect(self, data=None):
        self._stack.disconnect(self._on_notify_model_id)

    def _on_notify_mode(self, stack, param):
        #Slide out artist list on switching to artists view
        if stack.get_visible_child() == self.views[1]:
            stack.get_visible_child().stack.set_visible_child_name("dummy")
            stack.get_visible_child().stack.set_visible_child_name("artists")

    def _toggle_view(self, btn, i):
        self._stack.set_visible_child(self.views[i])
