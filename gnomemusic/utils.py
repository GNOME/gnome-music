# Copyright (c) 2016 Marinus Schraal <mschraal@src.gnome.org>
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

import colorsys
from enum import IntEnum
from math import pow
from PIL import Image

from gettext import gettext as _


class View(IntEnum):
    """Enum for views"""
    EMPTY = 0
    ALBUM = 1
    ARTIST = 2
    SONG = 3
    PLAYLIST = 4
    SEARCH = 5


def get_album_title(item):
    """Returns the album title associated with the media item

    In case of an audio file the get_album call returns the
    album title and in case of a container we are looking for
    the title.

    :param item: A Grilo Media object
    :return: The album title
    :rtype: string
    """
    album = item.get_album()

    if not album:
        album = get_media_title(item)

    return album


def get_artist_name(item):
    """Returns the preferred artist for a media item.

    The artist name for a particular media item can be either
    the main artist of the full album (album artist), the
    artist of the song (artist) or possibly it is not known at
    all. The first is preferred in most cases, because it is
    the most accurate in an album setting.

    :param item: A Grilo Media object
    :return: The artist name
    :rtype: string
    """

    return (item.get_album_artist()
            or item.get_artist()
            or _("Unknown Artist"))


def get_media_title(item):
    """Returns the title of the media item.

    :param item: A Grilo Media object
    :return: The title
    :rtype:
    """

    return (item.get_title()
            or _("Untitled"))


def get_media_year(item):
    """Returns the year when the media was created.

    :param item: A Grilo Media object
    :return: The creation year or None if not defined
    :rtype: string
    """
    date = item.get_creation_date()

    if not date:
        return None

    return str(date.get_year())


def seconds_to_string(duration):
    """Convert a time in seconds to a mm:ss string

    :param int duration: Time in seconds
    :return: Time in mm:ss format
    :rtype: string
    """
    seconds = duration
    minutes = seconds // 60
    seconds %= 60

    return '{:d}:{:02d}'.format(minutes, seconds)


def relative_luminance(r, g, b):
    """Compute relative luminance of an RGB color.

    Relative luminance is the relative brightness of any point in a
    colorspace, normalized to 0 for darkest black and 1 for lightest
    white.
    See: https://www.w3.org/TR/WCAG20/#relativeluminancedef
    :param float r: r channel between 0. and 1.
    :param float g: g channel between 0. and 1.
    :param float b: b channel between 0. and 1.
    :returns: relative luminance
    :rtype: float
    """
    params = []
    for channel in [r, g, b]:
        if channel <= 0.03928:
            value = channel / 12.92
        else:
            value = pow((channel + 0.055) / 1.055, 2.4)
        params.append(value)

    luminance = 0.2126 * params[0] + 0.7152 * params[1] + 0.0722 * params[2]
    return luminance


def contrast_ratio(r1, g1, b1, r2, g2, b2):
    """Compute contrast ratio between two RGB colors.

    Contrat ratio is a measure to indicate how readable the color
    combination is.
    See: https://www.w3.org/TR/WCAG20/#contrast-ratiodef
    :param float r1: r channel from color 1 between 0. and 1.
    :param float g1: g channel from color 1 between 0. and 1.
    :param float b1: b channel from color 1 between 0. and 1.
    :param float r2: r channel from color 2 between 0. and 1.
    :param float g2: g channel from color 2 between 0. and 1.
    :param float b2: b channel from color 2 between 0. and 1.
    :returns: constrat ratio
    :rtype: float
    """
    l1 = relative_luminance(r1, g1, b1)
    l2 = relative_luminance(r2, g2, b2)
    l_max = max(l1, l2)
    l_min = min(l1, l2)
    return (l_max + 0.05) / (l_min + 0.05)


def dominant_color(image):
    """Compute dominant color of a pillow image.

    Compute dominant color by extracting the peak of the hue channel of
    the image's histogram.
    :param Image image: a pillow image
    :returns: dominant color
    :rtype: (r, b, g) between 0. and 1.

    """
    # reduce image size if necessary to minimize computation time
    if (image.width > 256
            or image.height > 256):
        image.thumbnail((256, 256), Image.ANTIALIAS)

    im_hsv = image.convert('HSV')
    histogram = im_hsv.histogram()[:256]
    h_max = max(histogram)
    h_max_value = histogram.index(h_max)

    px = im_hsv.load()
    width = image.size[0]
    height = image.size[1]

    s_max_value = 0
    v_max_value = 0
    for i in range(width):
        for j in range(height):
            pixel = px[i, j]
            if pixel[0] == h_max_value:
                s_max_value += pixel[1]
                v_max_value += pixel[2]

    s_max_value /= h_max
    v_max_value /= h_max
    r, g, b = colorsys.hsv_to_rgb(
        h_max_value / 255.0, s_max_value / 255.0, v_max_value / 255.0)
    return r, g, b
