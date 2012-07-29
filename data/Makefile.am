NULL=

desktopdir = $(datadir)/applications
desktop_in_files = gnome-music.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)

%.ini: %.ini.in
	LC_ALL=C $(INTLTOOL_MERGE) -d -u -c $(top_builddir)/po/.intltool-merge-cache $(top_srcdir)/po $< $@

@INTLTOOL_DESKTOP_RULE@

EXTRA_DIST = \
	gnome-music.desktop.in.in	\
	$(NULL)

CLEANFILES = $(service_DATA)
DISTCLEANFILES = \
	gnome-music.desktop \
	gnome-music.desktop.in
