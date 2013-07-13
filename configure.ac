AC_PREREQ(2.63)
AC_INIT([gnome-music],
        [0.3], 
        [https://bugzilla.gnome.org/enter_bug.cgi?product=gnome-music],
        [gnome-music],
        [https://live.gnome.org/Design/Apps/Music])
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([Makefile.am])
AC_CONFIG_HEADERS(config.h)
AM_INIT_AUTOMAKE([1.13 tar-ustar dist-xz no-dist-gzip -Wno-portability])
AM_MAINTAINER_MODE([enable])

AM_PATH_PYTHON([3])

GETTEXT_PACKAGE=gnome-music
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE",
                   [The prefix for our gettext translation domains.])
IT_PROG_INTLTOOL(0.26)

AC_PROG_CC
AM_PROG_CC_C_O
LT_INIT([disable-static])

PKG_PROG_PKG_CONFIG([0.22])

GLIB_GSETTINGS
GOBJECT_INTROSPECTION_REQUIRE([1.35.9])
PKG_CHECK_MODULES([GTK], [gtk+-3.0 >= 3.9.8])

GRL_MIN_VERSION=0.2.7
PKG_CHECK_MODULES(GRL, grilo-0.2 >= $GRL_MIN_VERSION)

AC_CONFIG_FILES([
  Makefile
  data/Makefile
  gnome-music/Makefile
  po/Makefile.in
])
AC_OUTPUT
