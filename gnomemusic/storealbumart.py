import gi
gi.require_version("MediaArt", "2.0")
from gi.repository import Gio, GLib, GObject, MediaArt

from gnomemusic.musiclogger import MusicLogger


class StoreAlbumArt(GObject.GObject):

    def __init__(self, corealbum, media):
        """
        """
        super().__init__()

        self._corealbum = corealbum
        self._log = MusicLogger()
        self._media = media

        uri = media.get_thumbnail()
        if (uri is None
                or uri == ""):
            self._corealbum.props.thumbnail = "generic"
            return

        src = Gio.File.new_for_uri(uri)
        src.read_async(
            GLib.PRIORITY_LOW, None, self._read_callback, None)

    def _read_callback(self, src, result, data):
        try:
            istream = src.read_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._corealbum.props.thumbnail = "generic"
            return

        try:
            [tmp_file, iostream] = Gio.File.new_tmp()
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._corealbum.props.thumbnail = "generic"
            return

        ostream = iostream.get_output_stream()
        # FIXME: Passing the iostream here, otherwise it gets
        # closed. PyGI specific issue?
        ostream.splice_async(
            istream, Gio.OutputStreamSpliceFlags.CLOSE_SOURCE
            | Gio.OutputStreamSpliceFlags.CLOSE_TARGET, GLib.PRIORITY_LOW,
            None, self._splice_callback, [tmp_file, iostream])

    def _delete_callback(self, src, result, data):
        try:
            src.delete_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))

    def _splice_callback(self, src, result, data):
        tmp_file, iostream = data

        iostream.close_async(
            GLib.PRIORITY_LOW, None, self._close_iostream_callback, None)

        try:
            src.splice_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._corealbum.props.thumbnail = "generic"
            return

        success, cache_path = MediaArt.get_path(
            self._corealbum.props.artist, self._corealbum.props.title, "album")

        if not success:
            self._corealbum.props.thumbnail = "generic"
            return

        try:
            # FIXME: I/O blocking
            MediaArt.file_to_jpeg(tmp_file.get_path(), cache_path)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._corealbum.props.thumbnail = "generic"
            return

        # FIXME: Also set media.
        self._corealbum.props.thumbnail = cache_path

        tmp_file.delete_async(
            GLib.PRIORITY_LOW, None, self._delete_callback, None)

    def _close_iostream_callback(self, src, result, data):
        try:
            src.close_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
