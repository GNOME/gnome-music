NULL =

AM_CPPFLAGS = \
	-include config.h \
	$(MUSIC_CFLAGS) \
	-DLOCALEDIR=\""$(localedir)"\" \
	-DPKGDATADIR=\""$(pkgdatadir)"\" \
	-DPKGLIBDIR=\""$(pkglibdir)"\" \
	-DGNOME_DESKTOP_USE_UNSTABLE_API \
	$(NULL)

AM_VALAFLAGS = \
        --vapidir=$(srcdir)/../vapi --pkg config --pkg custom \
	@MUSIC_PACKAGES@ \
	$(NULL)

bin_PROGRAMS = gnome-music

vala_sources = \
        music-app.vala \
        music-window.vala \
	main.vala \
	$(NULL)

gsettingsschema_in_files = org.gnome.Music.gschema.xml.in
gsettings_SCHEMAS = $(gsettingsschema_in_files:.xml.in=.xml)
.PRECIOUS: $(gsettings_SCHEMAS)

@INTLTOOL_XML_NOMERGE_RULE@

@GSETTINGS_RULES@

music-resources.c: music.gresource.xml app-menu.ui
	$(AM_V_GEN) $(GLIB_COMPILE_RESOURCES) $(srcdir)/music.gresource.xml \
		--target=$@ --sourcedir=$(srcdir) --c-name music --generate-source

gnome_music_SOURCES = \
        gtk-notification.c   \
	$(vala_sources) \
	$(NULL)

gnome_music_LDADD = $(MUSIC_LIBS) -lm

CLEANFILES = \
	$(vala_sources:.vala=.c) \
	$(gsettings_SCHEMAS) \
	*.vapi *.stamp

EXTRA_DIST = \
        gtk-notification.h   \
	music.gresource.xml \
	app-menu.ui \
	$(gsettingsschema_in_files)     \
	$(NULL)
