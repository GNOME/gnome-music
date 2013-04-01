NULL =

nodist_bin_SCRIPTS = gnome-music

jsdir = $(pkgdatadir)
dist_js_DATA = \
	albumArtCache.js \
	player.js \
	toolbar.js \
	application.js \
	gnome-music.in \
	grilo.js \
	query.js \
	widgets.js \
	window.js \
	main.js \
	package.js \
	searchbar.js \
	view.js \
	$(NULL)

gnome-music: gnome-music.in
	$(AM_V_GEN) sed \
		-e "s|[@]GJS@|$(GJS)|g" \
		-e "s|[@]PACKAGE_NAME@|$(PACKAGE_NAME)|g" \
		-e "s|[@]PACKAGE_VERSION@|$(PACKAGE_VERSION)|g" \
		-e "s|[@]prefix@|$(prefix)|g" \
		-e "s|[@]libdir@|$(libdir)|g" \
		-e "s|[@]pkgdatadir@|$(pkgdatadir)|g" \
		$< > $@
	@chmod +x $@

EXTRA_DIST = gnome-music.in
DISTCLEANFILES = gnome-music

-include $(top_srcdir)/git.mk
