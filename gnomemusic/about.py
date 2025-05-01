# aboutwindow.py
#
# Copyright 2022 Christopher Davis <christopherdavis@gnome.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-2.0-or-later

from gettext import gettext as _

from gi.repository import Adw, Gtk


def show_about(app_id, version, parent):
    developers = [
        "Abhinav Singh",
        "Adam Blanchet",
        "Adrian Solom",
        "Alberto Fanjul",
        "Alexander Mikhaylenko",
        "Alireza Shabani",
        "Alpesh Jamgade",
        "Andre Klapper",
        "Andreas Nilsson",
        "Apostol Bakalov",
        "Arnel A. Borja",
        "Ashwani Singh Tanwar",
        "Ashwin Mohan",
        "Atharva Veer",
        "Automeris Naranja",
        "Benoît Legat",
        "Bilal Elmoussaoui",
        "Billy Barrow",
        "Bruce Cowan",
        "Carlos Garnacho",
        "Carlos Soriano",
        "Chinmay Gurjar",
        "Christophe van den Abbeele",
        "Christopher Davis",
        "Clayton G. Hobbs",
        "Divyanshu Vishwakarma",
        "Dominique Leuenberger",
        "Eslam Mostafa",
        "Elias Entrup",
        "Erik Inkinen",
        "Evan Nehring",
        "Evandro Giovanini",
        "Ezike Ebuka",
        "Fabiano Fidêncio",
        "Feliks Weber",
        "Felipe Borges",
        "Florian Darfeuille",
        "Gaurav Narula",
        "Georges Basile Stavracas Neto",
        "Guillaume Quintard",
        "Gyanesh Malhotra",
        "Harry Xie",
        "Hugo Posnic",
        "Ishaan Shah",
        "Islam Bahnasy",
        "Jakub Steiner",
        "James A. Baker",
        "Jan Alexander Steffens",
        "Janne Körkkö",
        "Jan-Michael Brummer",
        "Jean Felder",
        "Jeremy Bicha",
        "Jesus Bermudez Velazquez",
        "Jordan Petridis",
        "Juan José González",
        "Juan Suarez",
        "Kainaat Singh",
        "Kalev Lember",
        "Kevin Haller",
        "Konstantin Pospelov",
        "Koushik Sahu",
        "Lucy Coleclough",
        "Marinus Schraal",
        "Michael Catanzaro",
        "Mohanna Datta Yelugoti",
        "Mpho Jele",
        "Nick Richards",
        "Niels De Graef",
        "Nikolay Yanchuk",
        "Nils Reuße",
        "Pablo Palácios",
        "Phil Dawson",
        "Piotr Drąg",
        "Prashant Tyagi",
        "Rafael Coelho",
        "Rashi Sah",
        "Rasmus Thomsen",
        "Reuben Dsouza",
        "Robert Greener",
        "Sabri Ünal",
        "Sagar Lakhani",
        "Sai Suman Prayaga",
        "Sam Hewitt",
        "Sam Thursfield",
        "Sambhav Kothari",
        "Seif Lotfy",
        "Shema Angelo Verlain",
        "Shivani Poddar",
        "Shivansh Handa",
        "Simon McVittie",
        "Sophie Herold",
        "Subhadip Jana",
        "Sumaid Syed",
        "Suyash Garg",
        "Tapasweni Pathak",
        "Tau Gärtli",
        "Taylor Garcia",
        "Tjipke van der Heide",
        "Vadim Rutkovsky",
        "Veerasamy Sevagen",
        "Vincent Cottineau",
        "Vineet Reddy",
        "Walt Shabani",
        "Weifang Lai",
        "Yann Delaby",
        "Yash Singh",
        "Yosef Or Boczko"
    ]

    designers = [
        "Allan Day",
        "Jakub Steiner",
        "William Jon McCann"
    ]

    about = Adw.AboutDialog(
        application_name=_("Music"),
        application_icon=app_id,
        developer_name=_("The GNOME Project"),
        developers=developers,
        designers=designers,
        # Translators should localize the following string which
        # will be displayed at the bottom of the about box to give
        # credit to the translator(s).
        translator_credits=_("translator-credits"),
        version=version,
        website="https://apps.gnome.org/Music/",
        issue_url="https://gitlab.gnome.org/GNOME/gnome-music/-/issues/",
        copyright=_("© The GNOME Music Developers"),
        license_type=Gtk.License.GPL_2_0)

    about.present(parent)
