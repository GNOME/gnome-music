# Copyright 2021 The GNOME Music developers
#
# GNOME Music is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# GNOME Music is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with GNOME Music; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# The GNOME Music authors hereby grant permission for non-GPL compatible
# GStreamer plugins to be used and distributed together with GStreamer
# and GNOME Music.  This permission is above and beyond the permissions
# granted by the GPL license by which GNOME Music is covered.  If you
# modify this code, you may extend this exception to your version of the
# code, but you are not obligated to do so.  If you do not wish to do so,
# delete this exception statement from your version.

from typing import Dict, Tuple

from gi.repository import GObject


class AsyncQueue(GObject.GObject):
    """Queue async classes

    Allows for queueing async class calls and limit the amount of
    concurrent async operations ongoing. This to alleviate the
    pressure of having numerous ongoing async tasks that do IO or
    networking.

    A queued class must have a `start` function which starts the
    async task and a `finished` signal, which indicates it is done.
    The signal may be used by the caller and have an arbitrary
    number and type of arguments.
    The query function's first argument should be the async class and
    may have an arbitrary number of arguments following.
    """

    def __init__(self) -> None:
        """Initialize AsyncQueue
        """
        super().__init__()

        self._async_pool: Dict[int, Tuple] = {}
        self._async_active_pool: Dict[int, Tuple] = {}
        self._max_async = 4

    def queue(self, *args) -> None:
        """Queue an async call

        :param *args: The first item should be an async class, the
            following arbitrary numbers of arguments are to be passed
            to the `start` call of the given class.
            See the class doc for more information.
        """
        async_obj = args[0]
        async_obj_id = id(async_obj)
        result_id = 0

        if (async_obj_id not in self._async_pool
                and async_obj_id not in self._async_active_pool):
            self._async_pool[async_obj_id] = (args)
        else:
            return

        def on_async_finished(*args):
            async_obj = args[0]
            async_obj.disconnect(result_id)
            self._async_active_pool.pop(id(async_obj))

            if len(self._async_pool) > 0:
                key = list(self._async_pool.keys())[0]
                args = self._async_pool.pop(key)
                self.queue(*args)

        if len(self._async_active_pool) < self._max_async:
            async_task = self._async_pool.pop(async_obj_id)
            async_obj = async_task[0]
            self._async_active_pool[async_obj_id] = async_obj

            result_id = async_obj.connect("finished", on_async_finished)
            async_obj.start(*args[1:])
