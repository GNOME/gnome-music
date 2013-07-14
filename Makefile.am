ACLOCAL_AMFLAGS = -I m4 -I libgd
NULL =

bin_SCRIPTS = gnome-music

SUBDIRS = libgd gnomemusic data po

EXTRA_DIST = \
	AUTHORS.in \
	gnome-music.in
	$(NULL)

CLEANFILES = \
	$(bin_SCRIPTS)
	$(NULL)

MAINTAINERCLEANFILES = \
	$(srcdir)/AUTHORS \
	$(srcdir)/INSTALL \
	$(srcdir)/aclocal.m4 \
	$(srcdir)/autoscan.log \
	$(srcdir)/compile \
	$(srcdir)/config.guess \
	$(srcdir)/config.h.in \
	$(srcdir)/config.sub \
	$(srcdir)/configure.scan \
	$(srcdir)/depcomp \
	$(srcdir)/install-sh \
	$(srcdir)/ltmain.sh \
	$(srcdir)/missing \
	$(srcdir)/mkinstalldirs \
	$(NULL)

GITIGNOREFILES = \
	m4 \
	$(NULL)

dist-hook: gen-AUTHORS

gen-AUTHORS:
	$(AM_V_GEN)if test -d $(srcdir)/.git; then                      \
	   out="`cd $(srcdir) && git log --pretty=format:'%aN <%aE>' | sort -u`" && \
	   perl -p -e "s/#authorslist#// and print '$$out'"            \
	     < $(srcdir)/AUTHORS.in > $(distdir)/AUTHORS-tmp &&        \
	   mv -f $(distdir)/AUTHORS-tmp $(distdir)/AUTHORS ;           \
	fi

-include $(top_srcdir)/git.mk

