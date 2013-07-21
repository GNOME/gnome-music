import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop


class MediaPlayer2Service(dbus.service.Object):
    MEDIA_PLAYER2_IFACE = 'org.mpris.MediaPlayer2'
    def __init__(self, app):
        DBusGMainLoop(set_as_default=True)
        name = dbus.service.BusName('org.mpris.MediaPlayer2.GnomeMusic', dbus.SessionBus())
        dbus.service.Object.__init__(self, name, '/org/mpris/MediaPlayer2')
        self.app = app

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_IFACE)
    def Raise(self):
        self.app.do_activate()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_IFACE)
    def Quit(self):
        self.app.quit()

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        return self.GetAll(interface_name)[property_name]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name == self.MEDIA_PLAYER2_IFACE:
            return {
                'CanQuit': True,
                'CanRaise': True,
                'HasTrackList': False,
                'Identity': 'Music',
                'DesktopEntry': 'gnome-music',
                'SupportedUriSchemes': [
                    'file'
                ],
                'SupportedMimeTypes': [
                    'application/ogg',
                    'audio/x-vorbis+ogg',
                    'audio/x-flac',
                    'audio/mpeg'
                ],
            }
        else:
            raise dbus.exceptions.DBusException(
                'org.mpris.MediaPlayer2.GnomeMusic',
                'This object does not implement the %s interface'
                % interface_name)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv')
    def Set(self, interface_name, property_name, new_value):
        if interface_name == self.MEDIA_PLAYER2_IFACE:
            pass
        else:
            raise dbus.exceptions.DBusException(
                'org.mpris.MediaPlayer2.GnomeMusic',
                'This object does not implement the %s interface'
                % interface_name)

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        pass
