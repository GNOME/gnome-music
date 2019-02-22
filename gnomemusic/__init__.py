# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Manish Sinha <manishsinha@ubuntu.com>
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

from itertools import chain
from time import time
import logging

logger = logging.getLogger(__name__)
tabbing = 0


def log(fn):
    """Decorator to log function details.

    Shows function signature, return value, time elapsed, etc.
    Logging will be done if the debug flag is set.
    :param fn: the function to be decorated
    :return: function wrapped for logging
    """
    if logger.getEffectiveLevel() > logging.DEBUG:
        return fn

    def wrapped(*v, **k):
        global tabbing
        name = fn.__qualname__
        filename = fn.__code__.co_filename.split('/')[-1]
        lineno = fn.__code__.co_firstlineno

        params = ", ".join(map(repr, chain(v, k.values())))

        if 'rateLimitedFunction' not in name:
            logger.debug("%s%s(%s)[%s:%s]", '|' * tabbing, name, params,
                         filename, lineno)
        tabbing += 1
        start = time()
        retval = fn(*v, **k)
        elapsed = time() - start
        tabbing -= 1
        elapsed_time = ''
        if elapsed > 0.1:
            elapsed_time = ', took %02f' % elapsed
        if (elapsed_time
                or retval is not None):
            if 'rateLimitedFunction' not in name:
                logger.debug("%s  returned %s%s", '|' * tabbing, repr(retval),
                             elapsed_time)
        return retval

    return wrapped
