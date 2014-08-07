resource_files = $(shell $(GLIB_COMPILE_RESOURCES) --sourcedir=$(srcdir) --sourcedir=$(builddir) --generate-dependencies $(builddir)/gnome-music.gresource.xml) 
gnome-music.gresource: gnome-music.gresource.xml $(resource_files)
	$(AM_V_GEN) $(GLIB_COMPILE_RESOURCES) --target=$@ --sourcedir=$(srcdir) --sourcedir=$(builddir) $<

resourcedir = $(pkgdatadir)
resource_DATA = gnome-music.gresource

appsdir = $(datadir)/applications
apps_DATA = gnome-music.desktop

@INTLTOOL_DESKTOP_RULE@

appdatadir = $(datadir)/appdata
appdata_DATA = $(appdata_in_files:.xml.in=.xml)
appdata_in_files = gnome-music.appdata.xml.in

@INTLTOOL_XML_RULE@

man1_MANS = gnome-music.1

# hicolor icons
hicolor_icon16dir = $(datadir)/icons/hicolor/16x16/apps
hicolor_icon16_DATA = icons/hicolor/16x16/apps/gnome-music.png
hicolor_icon22dir = $(datadir)/icons/hicolor/22x22/apps
hicolor_icon22_DATA = icons/hicolor/22x22/apps/gnome-music.png
hicolor_icon32dir = $(datadir)/icons/hicolor/32x32/apps
hicolor_icon32_DATA = icons/hicolor/32x32/apps/gnome-music.png
hicolor_icon48dir = $(datadir)/icons/hicolor/48x48/apps
hicolor_icon48_DATA = icons/hicolor/48x48/apps/gnome-music.png
hicolor_icon256dir = $(datadir)/icons/hicolor/256x256/apps
hicolor_icon256_DATA = icons/hicolor/256x256/apps/gnome-music.png
hicolor_icon_files = \
	$(hicolor_icon16_DATA) \
	$(hicolor_icon22_DATA) \
	$(hicolor_icon32_DATA) \
	$(hicolor_icon48_DATA) \
	$(hicolor_icon256_DATA) \
	icons/hicolor/gnome-music.svg

hicontrast_icon16dir = $(datadir)/icons/HighContrast/16x16/apps
hicontrast_icon16_DATA = icons/HighContrast/16x16/apps/gnome-music.png
hicontrast_icon22dir = $(datadir)/icons/HighContrast/22x22/apps
hicontrast_icon22_DATA = icons/HighContrast/22x22/apps/gnome-music.png
hicontrast_icon32dir = $(datadir)/icons/HighContrast/32x32/apps
hicontrast_icon32_DATA = icons/HighContrast/32x32/apps/gnome-music.png
hicontrast_icon48dir = $(datadir)/icons/HighContrast/48x48/apps
hicontrast_icon48_DATA = icons/HighContrast/48x48/apps/gnome-music.png
hicontrast_icon256dir = $(datadir)/icons/HighContrast/256x256/apps
hicontrast_icon256_DATA = icons/HighContrast/256x256/apps/gnome-music.png
hicontrast_icon_files = \
	$(hicontrast_icon16_DATA) \
	$(hicontrast_icon22_DATA) \
	$(hicontrast_icon32_DATA) \
	$(hicontrast_icon48_DATA) \
	$(hicontrast_icon256_DATA)

gtk_update_hicontrast_icon_cache = gtk-update-icon-cache -f -t $(datadir)/icons/HighContrast

install-data-hook: update-icon-cache
uninstall-hook: update-icon-cache
update-icon-cache:
	@-if test -z "$(DESTDIR)"; then \
		echo "Updating Gtk hicolor icon cache."; \
		$(gtk_update_hicolor_icon_cache); \
		echo "Updating Gtk highcontrast icon cache."; \
		$(gtk_update_hicolor_icon_cache); \
	else \
		echo "*** Icon cache not updated.  After (un)install, run this:"; \
		echo "***   $(gtk_update_hicolor_icon_cache)"; \
		echo "***   $(gtk_update_hicolor_icon_cache)"; \
	fi


gsettings_SCHEMAS = org.gnome.Music.gschema.xml

# For uninstalled use
gschemas.compiled: $(gsettings_SCHEMAS) Makefile
	$(AM_V_GEN) $(GLIB_COMPILE_SCHEMAS) $(builddir)

@GSETTINGS_RULES@

EXTRA_DIST = \
	$(hicolor_icon_files) \
	$(hicontrast_icon_files) \
	$(resource_files) \
	gnome-music.appdata.xml.in \
	gnome-music.desktop.in \
	gnome-music.gresource.xml \
	org.gnome.Music.gschema.xml \
	$(man1_MANS) \
	$(NULL)

CLEANFILES = \
	gnome-music.gresource \
	gnome-music.appdata.xml \
	$(apps_DATA) \
	*.valid \
	gschemas.compiled \
	$(NULL)

all-local: gschemas.compiled

-include $(top_srcdir)/git.mk
