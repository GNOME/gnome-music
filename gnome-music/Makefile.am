appdir = $(pythondir)/gnomemusic/

app_PYTHON = \
	application.py \
	__init__.py \
	player.py \
	toolbar.py \
	view.py \
	window.py

bin_SCRIPTS = gnome-music
CLEANFILES = $(bin_SCRIPTS)
EXTRA_DIST = gnome-music.in

do_substitution = sed -e 's,[@]pythondir[@],$(pythondir),g' \
		      -e 's,[@]PACKAGE[@],$(PACKAGE),g' \
		      -e 's,[@]VERSION[@],$(VERSION),g' 

gnome-music: gnome-music.in Makefile
	$(do_substitution) < $(srcdir)/gnome-music.in > gnome-music
	chmod +x gnome-music
