from gi.repository import Gtk, Gio, GLib, Tracker
from gettext import gettext as _

from gnomemusic.toolbar import Toolbar
from gnomemusic.player import Player, SelectionToolbar
import gnomemusic.view as Views
from gnomemusic.query import Query

tracker = Tracker.SparqlConnection.get(None)


class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title=_('Music'))
        settings = Gio.Settings.new('org.gnome.Music')
        self.add_action(settings.create_action('repeat'))
        self.set_size_request(887, 640)
        self._setupView()
        self.proxy = Gio.DBusProxy.new_sync(Gio.bus_get_sync(Gio.BusType.SESSION, None),
                                            Gio.DBusProxyFlags.NONE,
                                            None,
                                            'org.gnome.SettingsDaemon',
                                            '/org/gnome/SettingsDaemon/MediaKeys',
                                            'org.gnome.SettingsDaemon.MediaKeys',
                                            None)
        self.proxy.call_sync('GrabMediaPlayerKeys',
                             GLib.Variant.new('(su)', 'Music'),
                             Gio.DBusCallFlags.NONE,
                             -1,
                             None)
        self.proxy.connect('g-signal', self._handleMediaKeys)

    def _windowsFocusCb(self, window, event):
        self.proxy.call_sync('GrabMediaPlayerKeys',
                             GLib.Variant.new('(su)', 'Music'),
                             Gio.DBusCallFlags.NONE,
                             -1,
                             None)

    def _handleMediaKeys(self, proxy, sender, signal, parameters):
        if signal != 'MediaPlayerKeyPressed':
            print('Received an unexpected signal \'%s\' from media player'.format(signal))
            return

        key = parameters.get_child_value(1).get_string()[0]
        if key == 'Play':
            self.player.PlayPause()
        elif key == 'Stop':
            self.player.Stop()
        elif key == 'Next':
            self.player.Next()
        elif key == 'Previous':
            self.player.Previous()

    def _setupView(self):
        self._box = Gtk.VBox()
        self.player = Player()
        self.selectionToolbar = SelectionToolbar()
        self.toolbar = Toolbar()
        self.set_titlebar(self.toolbar.headerBar)
        self.views = []
        self._stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=100,
            visible=True)
        self._box.pack_start(self._stack, True, True, 0)
        self._box.pack_start(self.player.eventBox, False, False, 0)
        self._box.pack_start(self.selectionToolbar.eventbox, False, False, 0)
        self.add(self._box)
        count = 1
        cursor = tracker.query(Query.SONGS_COUNT, None)
        if cursor is not None and cursor.next(None):
            count = cursor.get_integer(0)
        if count > 0:
            self.views.append(Views.Albums(self.toolbar, self.selectionToolbar, self.player))
            self.views.append(Views.Artists(self.toolbar, self.selectionToolbar, self.player))
            self.views.append(Views.Songs(self.toolbar, self.selectionToolbar, self.player))
            self.views.append(Views.Playlists(self.toolbar, self.selectionToolbar, self.player))

            for i in self.views:
                self._stack.add_titled(
                    self.views[i],
                    self.views[i].title,
                    self.views[i].title
                )

            self._onNotifyModelId = self._stack.connect("notify::visible-child", self._onNotifyMode)
            self.connect("destroy", self._stack.disconnect(self._onNotifyModelId))

            self.views[0].populate()
        #To revert to the No Music View when no songs are found
        else:
            self.views[0] = Views.Empty(self.toolbar, self.player)
            self._stack.add_titled(self.views[0], "Empty", "Empty")

        self.toolbar.header_bar.show()
        self.player.eventBox.show_all()
        self._box.show()
        self.show()

    def _onNotifyMode(self, stack, param):
        #Slide out artist list on switching to artists view
        if stack.get_visible_child() == self.views[1]:
            stack.get_visible_child().stack.set_visible_child_name("dummy")
            stack.get_visible_child().stack.set_visible_child_name("artists")

    def _toggleView(self, btn, i):
        self._stack.set_visible_child(self.views[i])
