resource_files = $(shell $(GLIB_COMPILE_RESOURCES) --sourcedir=$(srcdir) --generate-dependencies $(srcdir)/gnome-music.gresource.xml)
gnome-music.gresource: gnome-music.gresource.xml $(resource_files)
	$(AM_V_GEN) $(GLIB_COMPILE_RESOURCES) --target=$@ --sourcedir=$(srcdir) $<

resourcedir = $(pkgdatadir)
resource_DATA = gnome-music.gresource

appsdir = $(datadir)/applications
apps_DATA = gnome-music.desktop

# icons
icon16dir = $(datadir)/icons/hicolor/16x16/apps
icon16_DATA = icons/hicolor/16x16/apps/gnome-music.png
icon22dir = $(datadir)/icons/hicolor/22x22/apps
icon22_DATA = icons/hicolor/22x22/apps/gnome-music.png
icon32dir = $(datadir)/icons/hicolor/32x32/apps
icon32_DATA = icons/hicolor/32x32/apps/gnome-music.png
icon48dir = $(datadir)/icons/hicolor/48x48/apps
icon48_DATA = icons/hicolor/48x48/apps/gnome-music.png
icon256dir = $(datadir)/icons/hicolor/256x256/apps
icon256_DATA = icons/hicolor/256x256/apps/gnome-music.png
icon_files = \
	$(icon16_DATA) \
	$(icon22_DATA) \
	$(icon32_DATA) \
	$(icon48_DATA) \
	$(icon256_DATA) \
	icons/hicolor/gnome-music.svg

gtk_update_icon_cache = gtk-update-icon-cache -f -t $(datadir)/icons/hicolor

install-data-hook: update-icon-cache
uninstall-hook: update-icon-cache
update-icon-cache:
	@-if test -z "$(DESTDIR)"; then \
		echo "Updating Gtk icon cache."; \
		$(gtk_update_icon_cache); \
	else \
		echo "*** Icon cache not updated.  After (un)install, run this:"; \
		echo "***   $(gtk_update_icon_cache)"; \
	fi


@INTLTOOL_DESKTOP_RULE@

gsettings_SCHEMAS = org.gnome.Music.gschema.xml

@GSETTINGS_RULES@

EXTRA_DIST = \
	$(icon_files) \
	$(resource_files) \
	gnome-music.desktop.in \
	gnome-music.gresource.xml \
	org.gnome.Music.gschema.xml \
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
