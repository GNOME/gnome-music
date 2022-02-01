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

from typing import Any, Dict, List, Optional, Tuple
import time

from gi.repository import GObject, GLib

from gnomemusic.musiclogger import MusicLogger
from gnomemusic.prioritypool import PriorityPool


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

    def __init__(self, queue_name: Optional[str] = None) -> None:
        """Initialize AsyncQueue

        :param str queue_name: The user facing name of this queue or
            None for the generic class identifier
        """
        super().__init__()

        self._async_pool: Dict[int, Tuple] = {}
        self._async_pool_coreobject_hash: Dict = {}
        self._async_active_pool: Dict[int, Tuple] = {}
        self._async_data: Dict[object, Tuple[int, float]] = {}
        self._log = MusicLogger()
        self._max_async = 4
        self._priority_pool = PriorityPool()
        self._queue_name = queue_name if queue_name else self
        self._timeout_id = 0

    def queue(self, *args: Any) -> None:
        """Queue an async call

        :param *args: The first item should be an async class, the
            following arbitrary numbers of arguments are to be passed
            to the `start` call of the given class.
            See the class doc for more information.
        """
        async_obj_id = id(args[0])

        if (async_obj_id not in self._async_pool
                and async_obj_id not in self._async_active_pool):
            self._async_pool[async_obj_id] = (args)
            self._async_pool_coreobject_hash[async_obj_id] = id(args[1])

        if self._timeout_id == 0:
            self._timeout_id = GLib.timeout_add(100, self._dispatch)

    def _dispatch(self) -> bool:
        tick = time.time()
        common_ids = self._common_ids()

        while len(self._async_active_pool) < self._max_async:
            if len(self._async_pool) == 0:
                self._timeout_id = 0
                return GLib.SOURCE_REMOVE

            if common_ids:
                async_obj_id = common_ids.pop()
            else:
                async_obj_id = list(self._async_pool.keys())[0]

            # IDs may not match the ones in the async pool as
            # PriorityPool can contain any kind of coreobject.
            try:
                async_task_args = self._async_pool.pop(async_obj_id)
            except KeyError:
                continue
            else:
                self._async_pool_coreobject_hash.pop(async_obj_id)

            async_obj = async_task_args[0]
            self._async_active_pool[async_obj_id] = async_task_args

            self._async_data[async_obj] = (
                async_obj.connect("finished", self._on_async_finished),
                tick)
            async_obj.start(*async_task_args[1:])

        return GLib.SOURCE_CONTINUE

    def _on_async_finished(
            self, obj: Any, *signal_args: Any) -> None:
        handler_id, tick = self._async_data.pop(obj)
        t = (time.time() - tick) * 1000
        self._log.debug(f"{self._queue_name}: {t:.2f} ms task")

        a = len(self._async_active_pool)
        self._log.debug(
            f"{self._queue_name}: "
            f"{a} active task(s) of {len(self._async_pool) + a}")

        obj.disconnect(handler_id)
        self._async_active_pool.pop(id(obj))

    def _common_ids(self) -> List[int]:
        return list(set(self._priority_pool.props.pool).intersection(
            self._async_pool_coreobject_hash.values()))
