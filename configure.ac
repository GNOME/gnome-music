AC_PREREQ([2.67])
AC_INIT([gnome-music],[0.0.0],[https://github.com/openshine/gnome-music])
AC_CONFIG_SRCDIR([src/main.vala])
AC_CONFIG_HEADERS([config.h])
AC_CONFIG_MACRO_DIR([m4])
AM_INIT_AUTOMAKE
# Enable silent rules is available
AM_SILENT_RULES([yes])
AM_MAINTAINER_MODE([enable])
AC_CONFIG_FILES([Makefile
		src/Makefile
		data/Makefile
		po/Makefile.in
		data/gnome-music.desktop.in
		])

LT_INIT
AC_PROG_CC
AM_PROG_VALAC([0.16])
AC_PROG_INSTALL

GLIB_GSETTINGS

# i18n stuff
IT_PROG_INTLTOOL([0.40])

AM_GNU_GETTEXT([external])
AM_GNU_GETTEXT_VERSION([0.17])

GETTEXT_PACKAGE=gnome-music
AC_DEFINE_UNQUOTED([GETTEXT_PACKAGE], ["$GETTEXT_PACKAGE"], [Gettext Package])
AC_SUBST(GETTEXT_PACKAGE)


pkg_modules="gtk+-3.0 >= 3.4.0
	     glib-2.0 >= 2.31.10
	     gnome-desktop-3.0
	     libnotify
	     gee-1.0
	     "
PKG_CHECK_MODULES(MUSIC, [$pkg_modules])

MUSIC_PACKAGES="--pkg gtk+-3.0 --pkg gio-2.0 --pkg gio-unix-2.0 --pkg libnotify"
AC_SUBST(MUSIC_PACKAGES)

#############
# Resources #
#############

GLIB_COMPILE_RESOURCES=`$PKG_CONFIG --variable glib_compile_resources gio-2.0`
AC_SUBST(GLIB_COMPILE_RESOURCES)

AC_OUTPUT
