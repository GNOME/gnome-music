resource_files = $(shell $(GLIB_COMPILE_RESOURCES) --sourcedir=$(srcdir) --sourcedir=$(builddir) --generate-dependencies $(builddir)/gnome-music.gresource.xml) 
gnome-music.gresource: gnome-music.gresource.xml $(resource_files)
	$(AM_V_GEN) $(GLIB_COMPILE_RESOURCES) --target=$@ --sourcedir=$(srcdir) --sourcedir=$(builddir) $<

resourcedir = $(pkgdatadir)
resource_DATA = gnome-music.gresource

appsdir = $(datadir)/applications
apps_DATA = org.gnome.Music.desktop

@INTLTOOL_DESKTOP_RULE@

appdatadir = $(datadir)/appdata
appdata_DATA = $(appdata_in_files:.xml.in=.xml)
appdata_in_files = gnome-music.appdata.xml.in

@INTLTOOL_XML_RULE@

man1_MANS = gnome-music.1

# hicolor icons
hicolor_icon16dir = $(datadir)/icons/hicolor/16x16/apps
hicolor_icon16_DATA = icons/hicolor/16x16/apps/org.gnome.Music.png
hicolor_icon22dir = $(datadir)/icons/hicolor/22x22/apps
hicolor_icon22_DATA = icons/hicolor/22x22/apps/org.gnome.Music.png
hicolor_icon32dir = $(datadir)/icons/hicolor/32x32/apps
hicolor_icon32_DATA = icons/hicolor/32x32/apps/org.gnome.Music.png
hicolor_icon48dir = $(datadir)/icons/hicolor/48x48/apps
hicolor_icon48_DATA = icons/hicolor/48x48/apps/org.gnome.Music.png
hicolor_icon256dir = $(datadir)/icons/hicolor/256x256/apps
hicolor_icon256_DATA = icons/hicolor/256x256/apps/org.gnome.Music.png
hicolor_iconsymbolicdir = $(datadir)/icons/hicolor/symbolic/apps
hicolor_iconsymbolic_DATA = icons/hicolor/symbolic/apps/org.gnome.Music-symbolic.svg
hicolor_icon_files = \
	$(hicolor_icon16_DATA) \
	$(hicolor_icon22_DATA) \
	$(hicolor_icon32_DATA) \
	$(hicolor_icon48_DATA) \
	$(hicolor_icon256_DATA) \
	$(hicolor_iconsymbolic_DATA) \
	icons/hicolor/gnome-music.svg

gtk_update_icon_cache = gtk-update-icon-cache -f -t

install-data-hook: update-icon-cache
uninstall-hook: update-icon-cache
update-icon-cache:
	@-if test -z "$(DESTDIR)"; then \
		echo "Updating Gtk hicolor icon cache."; \
		$(gtk_update_icon_cache) $(datadir)/icons/hicolor; \
	else \
		echo "*** Icon cache not updated.  After (un)install, run this:"; \
		echo "***   $(gtk_update_icon_cache) $(datadir)/icons/hicolor"; \
	fi


gsettings_SCHEMAS = org.gnome.Music.gschema.xml

# For uninstalled use
gschemas.compiled: $(gsettings_SCHEMAS) Makefile
	$(AM_V_GEN) $(GLIB_COMPILE_SCHEMAS) $(builddir)

@GSETTINGS_RULES@

EXTRA_DIST = \
	$(hicolor_icon_files) \
	$(resource_files) \
	gnome-music.appdata.xml.in \
	org.gnome.Music.desktop.in \
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
