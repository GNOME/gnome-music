AC_PREREQ([2.67])
AC_INIT([gnome-music],[0.0.0],[https://github.com/tapia/gnome-music])
AC_CONFIG_SRCDIR([src/main.vala])
AC_CONFIG_HEADERS([config.h])
AM_INIT_AUTOMAKE
# Enable silent rules is available
AM_SILENT_RULES([yes])
AM_MAINTAINER_MODE([enable])

LT_INIT
AC_PROG_CC
AM_PROG_VALAC([0.17])
AC_PROG_INSTALL

GOBJECT_INTROSPECTION_REQUIRE([0.9.6])

GLIB_GSETTINGS

# i18n stuff
IT_PROG_INTLTOOL([0.40])

AM_GNU_GETTEXT([external])
AM_GNU_GETTEXT_VERSION([0.17])

GETTEXT_PACKAGE=gnome-music
AC_DEFINE_UNQUOTED([GETTEXT_PACKAGE], ["$GETTEXT_PACKAGE"], [Gettext Package])
AC_SUBST(GETTEXT_PACKAGE)

GLIB_MIN_VERSION=2.31.0
GTK_MIN_VERSION=3.4.0
GRILO_MIN_VERSION=0.2
GEE_MIN_VERSION=0.6.4
GOBJECT_INTROSPECTION_MIN_VERSION=0.9.6

PKG_CHECK_MODULES(MUSIC, [
  glib-2.0 >= $GLIB_MIN_VERSION
  gtk+-3.0 >= $GTK_MIN_VERSION
  grilo-0.2 >= $GRILO_MIN_VERSION
  gee-1.0 >= $GEE_MIN_VERSION
])

MUSIC_PACKAGES="--pkg glib-2.0 --pkg gtk+-3.0 --pkg grilo-0.2 --pkg gee-1.0"
AC_SUBST(MUSIC_PACKAGES)

LIBGD_INIT([
  gtk-hacks
  main-toolbar
  main-icon-view
  margin-container
  static
  tagged-entry
  vapi
])

AC_CONFIG_FILES([Makefile
                 vapi/Makefile
                 vapi/upstream/Makefile
                 src/Makefile
                 libgd/Makefile
                 data/Makefile
                 po/Makefile.in
                 data/gnome-music.desktop.in
                 ])

AC_OUTPUT
