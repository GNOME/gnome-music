resource_files = $(shell $(GLIB_COMPILE_RESOURCES) --sourcedir=$(srcdir) --generate-dependencies $(srcdir)/gnome-music.gresource.xml)
gnome-music.gresource: gnome-music.gresource.xml $(resource_files)
	$(AM_V_GEN) $(GLIB_COMPILE_RESOURCES) --target=$@ --sourcedir=$(srcdir) $<

resourcedir = $(pkgdatadir)
resource_DATA = gnome-music.gresource

appsdir = $(datadir)/applications
apps_DATA = gnome-music.desktop

@INTLTOOL_DESKTOP_RULE@


@GSETTINGS_RULES@

EXTRA_DIST = \
	CREDITS \
	gnome-music.desktop.in \
	gnome-music.gresource.xml \
	$(resource_files) \
	$(NULL)

CLEANFILES = \
	gnome-music.gresource \
	$(apps_DATA) \
	*.valid \
	gschemas.compiled \
	$(NULL)

# For uninstalled use
all-local:
	$(GLIB_COMPILE_SCHEMAS) $(builddir)

-include $(top_srcdir)/git.mk
