AC_PREREQ(2.63)
AC_INIT([gnome-music],[0.2],
	[https://bugzilla.gnome.org/enter_bug.cgi?product=gnome-music],
	[gnome-music],
	[https://live.gnome.org/Design/Apps/Music])

AC_CONFIG_HEADERS([config.h])
AC_CONFIG_MACRO_DIR([m4])

AM_INIT_AUTOMAKE([1.11 dist-xz foreign tar-ustar -Wno-portability])

m4_ifdef([AM_SILENT_RULES],[AM_SILENT_RULES([yes])])

AC_PROG_CC
AM_PROG_CC_C_O
LT_INIT([disable-static])

LIBGD_INIT([header-bar main-toolbar main-view stack revealer gir])

PKG_PROG_PKG_CONFIG([0.22])

GLIB_GSETTINGS
GOBJECT_INTROSPECTION_REQUIRE([1.30.0])

AC_PATH_PROG([GJS],[gjs])

GLIB_COMPILE_RESOURCES=`$PKG_CONFIG --variable glib_compile_resources gio-2.0`
AC_SUBST(GLIB_COMPILE_RESOURCES)

AC_CONFIG_FILES([
  Makefile
  libgd/Makefile
  src/Makefile
])
AC_OUTPUT
