# Copyright 2020 The GNOME Music developers
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

import re

WEIGHTS = {
    "title": 25,
    "album": 15,
    "artist": 10,
    "date": 8,
    "album-artist": 6,
    "track-number": 4,
    "album-disc-number": 4
}


def levenshtein_distance(str_a, str_b):
    """Compute the levenshtein distance between two strings.

    It measures the difference between two sequences. It represents
    the minimum of edits (subsitution, edition, insertion) to change
    one string into the other.
    It is meant to be used or single word strings.

    :param str str_a: first word
    :param str str_b: second word
    :returns: levenshtein_distance
    :rtype: float
    """
    len_a = len(str_a)
    len_b = len(str_b)

    if (not str_a
            or not str_b):
        return len_a + len_b

    d = [[i] for i in range(len_a+1)]
    del d[0][0]
    d[0] = [j for j in range(len_b+1)]

    for i in range(1, len_a+1):
        for j in range(1, len_b+1):
            if str_a[i-1] == str_b[j-1]:
                cost = d[i-1][j-1]
            else:
                cost = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+2)

            d[i].insert(j, cost)

    return d[-1][-1]


def word_similarity(str_a, str_b):
    """Compute the similarity between two words.

    It is based on the levenshtein distance.
    1 means that the words are identical.
    0 means that the words are completely different.

    :param str str_a: first word
    :param str str_b: second word
    :returns: a score between 0 and 1.
    :rtype: float
    """
    distance = levenshtein_distance(str_a, str_b)
    length = float(len(str_a) + len(str_b))
    return (length - distance)/length


def sequence_similarity(list_a, list_b):
    """Compute the similarity between two list of words.

    It is based on a two-dimensional levenshtein distance.
    1 means that the words are identical.
    0 means that the words are completely different.

    :param list list_a:
    :param list list_b:
    :returns: similarity score between 0 and 1
    :rtype: float
    """
    len_a = len(list_a)
    len_b = len(list_b)

    if (len_a == 1
            and len_b == 1):
        return word_similarity(list_a[0], list_b[0])

    d = [[i] for i in range(len_a+1)]
    del d[0][0]
    d[0] = [j for j in range(len_b+1)]

    for i in range(1, len_a+1):
        str_a = list_a[i - 1]
        for j in range(1, len_b+1):
            str_b = list_b[j - 1]
            dis = levenshtein_distance(str_a, str_b)
            if dis == 0:
                cost = d[i-1][j-1]
            else:
                ratio = dis / (len(str_a) + len(str_b))
                cost = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+2*ratio)

            d[i].insert(j, cost)

    length = (len_a + len_b)
    return (length - d[-1][-1]) / length


def string_similarity(str_a, str_b):
    """Compute the similarity between two strings.

    It is based on the levenshtein distance. All the non
    word characters from the strings are removed to prevent
    wrong results.

    1 means that the strings are identical.
    0 means that the strings are completely different.

    :param str str_a: first string
    :param str str_b: second string
    :returns: similarity score between 0 and 1
    :rtype: float
    """
    words_regex = re.compile(r"\w+")
    words_a = re.findall(words_regex, str_a.lower())
    words_b = re.findall(words_regex, str_b.lower())

    return sequence_similarity(words_a, words_b)


def number_similarity(nr_a, nr_b):
    """Compute the similarity between two numbers.

    1 means that the numbers are identical.
    0 means that the numbers are different.

    :param int nr_a: first number
    :param int nr_b: second number
    :returns: similarity score between 0 and 1
    :rtype: float
    """
    if nr_a == nr_b:
        return 1.0

    return 0.0


def date_similarity(date_a, date_b):
    """Compute the similarity between two dates.

    1 means are year and month are indentical.
    0.95 means that the years are indentical.
    0.65 means that the years difference is lower than 3 years.
    0.25 means that the years difference is greater than 3 years.
    0 means that at least one of the date is missing.

    :param GLib.DateTime date_a: first date
    :param GLib.DateTime date_b: second date
    :returns: similarity score between 0 and 1
    :rtype: float
    """
    if (not date_a
            or not date_b):
        return 0.0

    year_a = date_a.get_year()
    year_b = date_b.get_year()
    if (not year_a
            or not year_b):
        return 0.0

    month_a = date_a.get_month()
    month_b = date_b.get_month()
    if year_a == year_b:
        if month_a == month_b:
            return 1.0
        return 0.95

    if abs(year_a - year_b) < 3:
        return 0.65

    return 0.25


def song_similarity(media_ref, media_cmp):
    """Compute a similarity score between two audio medias.

    It checks the main tags of a song to compute a similarity
    score based on the similarity score of each of the tags. Some
    weights are used to give more importance to the most important
    tags.
    media_ref is used as a reference media. It means that a tag
    similarity score won't be computed if it's not available in
    media_ref.

    A high score means a good similarity.

    :param Grl.Media media_ref: The reference media
    :param Grl.Media media_cmp: The compared media
    :returns: a similarity score between media_a and media_b
    :rtype: float
    """
    score = 0.0

    if media_ref.get_title():
        new_title = (media_cmp.get_title()
                     or "")
        title_score = string_similarity(media_ref.get_title(), new_title)
        score += title_score * WEIGHTS["title"]

    if media_ref.get_album():
        new_album = (media_cmp.get_album()
                     or "")
        album_score = string_similarity(media_ref.get_album(), new_album)
        score += album_score * WEIGHTS["album"]

    if media_ref.get_artist():
        new_artist = (media_cmp.get_artist()
                      or "")
        artist_score = string_similarity(media_ref.get_artist(), new_artist)
        score += artist_score * WEIGHTS["artist"]

    if media_ref.get_album_artist():
        new_album_artist = (media_cmp.get_album_artist()
                            or "")
        album_artist_score = string_similarity(
            media_ref.get_album_artist(), new_album_artist)
        score += album_artist_score * WEIGHTS["album-artist"]

    if media_ref.get_track_number():
        new_track_nr = (media_cmp.get_track_number()
                        or 0)
        track_nr_score = number_similarity(
            media_ref.get_track_number(), new_track_nr)
        score += track_nr_score * WEIGHTS["track-number"]

    if media_ref.get_album_disc_number():
        new_album_disc_nr = (media_cmp.get_album_disc_number()
                             or 0)
        album_disc_nr_score = number_similarity(
            media_ref.get_album_disc_number(), new_album_disc_nr)
        score += album_disc_nr_score * WEIGHTS["album-disc-number"]

    if media_ref.get_creation_date():
        date_score = date_similarity(
            media_ref.get_creation_date(), media_cmp.get_creation_date())
        score += date_score * WEIGHTS["date"]

    return score
