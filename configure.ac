AC_PREREQ(2.63)
AC_INIT([gnome-music],
        [3.24.2],
        [https://bugzilla.gnome.org/enter_bug.cgi?product=gnome-music],
        [gnome-music],
        [https://wiki.gnome.org/Apps/Music])
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([Makefile.am])
AC_CONFIG_HEADERS(config.h)
AM_INIT_AUTOMAKE([1.11 tar-ustar dist-xz no-dist-gzip -Wno-portability subdir-objects])
AM_MAINTAINER_MODE([enable])
m4_ifdef([AM_SILENT_RULES],[AM_SILENT_RULES([yes])])

AM_PATH_PYTHON([3.3])

GETTEXT_PACKAGE=gnome-music
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE",
                   [The prefix for our gettext translation domains.])
IT_PROG_INTLTOOL(0.26)

YELP_HELP_INIT

AC_PROG_CC
AM_PROG_CC_C_O
LT_INIT([disable-static])

LIBGD_INIT([main-view gir tagged-entry])

PKG_PROG_PKG_CONFIG([0.22])

GLIB_GSETTINGS
AX_REQUIRE_DEFINED([GOBJECT_INTROSPECTION_CHECK])
GOBJECT_INTROSPECTION_CHECK([1.35.9])
PKG_CHECK_MODULES([GTK], [gtk+-3.0 >= 3.19.3])
PKG_CHECK_MODULES([MEDIAART], [libmediaart-2.0 >= 1.9.1])

PYGOBJECT_MIN_VERSION=3.21.1
PKG_CHECK_MODULES(PYGOBJECT, [pygobject-3.0 >= $PYGOBJECT_MIN_VERSION])

TRACKER_MIN_VERSION=1.11.1
PKG_CHECK_MODULES(TRACKER, [tracker-sparql-1.0 >= $TRACKER_MIN_VERSION])

GLIB_COMPILE_RESOURCES=`$PKG_CONFIG --variable glib_compile_resources gio-2.0`
AC_SUBST(GLIB_COMPILE_RESOURCES)

GRL_MIN_VERSION=0.3.3
PKG_CHECK_MODULES(GRL, grilo-0.3 >= $GRL_MIN_VERSION)

AC_CONFIG_FILES([
  Makefile
  data/Makefile
  help/Makefile
  data/AboutDialog.ui
  gnomemusic/Makefile
  gnomemusic/views/Makefile
  gnomemusic/widgets/Makefile
  po/Makefile.in
  libgd/Makefile
])
AC_OUTPUT
