NULL =

AM_CPPFLAGS = \
	-include config.h 					\
	$(MUSIC_CFLAGS) 					\
	-DLOCALEDIR=\""$(localedir)"\" 		\
	-DPKGDATADIR=\""$(pkgdatadir)"\" 	\
	-DPKGLIBDIR=\""$(pkglibdir)"\" 		\
	-DGNOME_DESKTOP_USE_UNSTABLE_API 	\
	-I$(top_srcdir)/libgd               \
	$(NULL)

AM_VALAFLAGS = \
	--vapidir=$(srcdir)/			\
	--vapidir=$(top_srcdir)/libgd	\
    --vapidir=$(top_srcdir)/vapi	\
	--pkg config					\
	--pkg gd-1.0					\
	@MUSIC_PACKAGES@				\
	$(NULL)

bin_PROGRAMS = gnome-music

vala_sources = \
        music-app.vala          	\
        music-topbar.vala       	\
        music-player.vala       	\
		music-collection-view.vala	\
		music-list-store.vala		\
		music-playlist-view.vala	\
		music-album-info-box.vala	\
		music-playlist-songs.vala	\
		music-browse-history.vala	\
		music-utils.vala			\
		album-art-cache.vala		\
		main.vala               	\
		$(NULL)

gsettingsschema_in_files = org.gnome.Music.gschema.xml.in
gsettings_SCHEMAS = $(gsettingsschema_in_files:.xml.in=.xml)
.PRECIOUS: $(gsettings_SCHEMAS)

@INTLTOOL_XML_NOMERGE_RULE@

@GSETTINGS_RULES@

music-resources.c: music.gresource.xml app-menu.ui
	$(AM_V_GEN) $(GLIB_COMPILE_RESOURCES) $(srcdir)/music.gresource.xml \
		--target=$@ --sourcedir=$(srcdir) --c-name music --generate-source

gnome_music_SOURCES = 	\
	$(vala_sources) 	\
	$(NULL)

gnome_music_LDADD =	$(MUSIC_LIBS)					\
					$(top_builddir)/libgd/libgd.la	\
					$(NULL)

CLEANFILES = \
	$(vala_sources:.vala=.c) 	\
	$(gsettings_SCHEMAS) 		\
	*.vapi *.stamp

EXTRA_DIST = \
	music.gresource.xml 			\
	app-menu.ui 					\
	$(gsettingsschema_in_files)     \
	$(NULL)
