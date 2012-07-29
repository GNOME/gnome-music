NULL =

AM_CPPFLAGS = \
	-include config.h \
	$(CONTACTS_CFLAGS) \
	-DLOCALEDIR=\""$(localedir)"\" \
	-DPKGDATADIR=\""$(pkgdatadir)"\" \
	-DPKGLIBDIR=\""$(pkglibdir)"\" \
	-DGNOME_DESKTOP_USE_UNSTABLE_API \
	$(NULL)

AM_VALAFLAGS = \
	--vapidir=$(srcdir)/../vapi --pkg config --pkg custom \
	@CONTACTS_PACKAGES@ \
	$(NULL)

if USE_GSTREAMER
AM_VALAFLAGS += -D HAVE_GSTREAMER @CONTACTS_GSTREAMER_PACKAGES@
AM_CPPFLAGS += $(CONTACTS_GSTREAMER_CFLAGS)
endif

bin_PROGRAMS = gnome-music

vala_sources = \
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
	$(vala_sources) \
	$(NULL)

gnome_music_LDADD = $(CONTACTS_LIBS) -lm

if USE_GSTREAMER
gnome_music_LDADD += $(CONTACTS_GSTREAMER_LIBS)
gnome_music_SOURCES += \
	$(NULL)
endif

CLEANFILES = \
	$(vala_sources:.vala=.c) \
	$(gsettings_SCHEMAS) \
	*.vapi *.stamp

EXTRA_DIST = \
	contacts.gresource.xml \
	app-menu.ui \
	$(gsettingsschema_in_files)     \
	$(NULL)
