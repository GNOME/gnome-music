AUTOMAKE_OPTIONS=subdir-objects
NULL =
CLEANFILES =
MAINTAINERCLEANFILES =
EXTRA_DIST =
noinst_DATA =

AM_CPPFLAGS =					\
        -I$(top_srcdir)				\
        -DPREFIX=\"$(prefix)\"			\
        -DLIBDIR=\"$(libdir)\"			\
        -DG_LOG_DOMAIN=\"libgd\"		\
        -DG_DISABLE_DEPRECATED			\
        $(LIBGD_CFLAGS)				\
        $(NULL)

noinst_PROGRAMS =

if LIBGD_STATIC
noinst_LTLIBRARIES = libgd.la
else
pkglib_LTLIBRARIES = libgd.la
endif

libgd_la_LIBADD = $(LIBGD_LIBS) $(LIBM)
libgd_la_LDFLAGS = -avoid-version
libgd_la_SOURCES = libgd/gd.h
nodist_libgd_la_SOURCES =

catalog_sources =				\
	libgd/gd-types-catalog.c		\
	libgd/gd-types-catalog.h		\
	$(NULL)

nodist_libgd_la_SOURCES += $(catalog_sources)
EXTRA_DIST += $(catalog_sources)

if LIBGD_GTK_HACKS
gtk_hacks_sources =                             \
        libgd/gd-icon-utils.c		        \
        libgd/gd-icon-utils.h			\
        $(NULL)

nodist_libgd_la_SOURCES += $(gtk_hacks_sources)
EXTRA_DIST += $(gtk_hacks_sources)
endif

if LIBGD__BOX_COMMON
box_common_sources =				\
	libgd/gd-main-box-child.c		\
	libgd/gd-main-box-child.h		\
	libgd/gd-main-box-generic.c		\
	libgd/gd-main-box-generic.h		\
	libgd/gd-main-box-item.c		\
	libgd/gd-main-box-item.h		\
	$(NULL)

nodist_libgd_la_SOURCES += $(box_common_sources)
EXTRA_DIST += $(box_common_sources)
endif

if LIBGD_MAIN_ICON_BOX
main_icon_box_sources =				\
	libgd/gd-main-icon-box.c		\
	libgd/gd-main-icon-box.h		\
	libgd/gd-main-icon-box-child.c		\
	libgd/gd-main-icon-box-child.h		\
	libgd/gd-main-icon-box-icon.c		\
	libgd/gd-main-icon-box-icon.h		\
	$(NULL)

nodist_libgd_la_SOURCES += $(main_icon_box_sources)
EXTRA_DIST += $(main_icon_box_sources)
endif

if LIBGD_MAIN_BOX
main_box_sources =				\
	libgd/gd-main-box.c			\
	libgd/gd-main-box.h			\
	$(NULL)

nodist_libgd_la_SOURCES += $(main_box_sources)
EXTRA_DIST += $(main_box_sources)
endif

if LIBGD__VIEW_COMMON
view_common_sources =				\
	libgd/gd-main-view-generic.c		\
	libgd/gd-main-view-generic.h		\
	libgd/gd-styled-text-renderer.c		\
	libgd/gd-styled-text-renderer.h		\
	libgd/gd-two-lines-renderer.c		\
	libgd/gd-two-lines-renderer.h		\
	$(NULL)

nodist_libgd_la_SOURCES += $(view_common_sources)
EXTRA_DIST += $(view_common_sources)
endif

if LIBGD_MAIN_ICON_VIEW
main_icon_view_sources =			\
	libgd/gd-main-icon-view.c		\
	libgd/gd-main-icon-view.h		\
	libgd/gd-toggle-pixbuf-renderer.c	\
	libgd/gd-toggle-pixbuf-renderer.h	\
	$(NULL)

nodist_libgd_la_SOURCES += $(main_icon_view_sources)
EXTRA_DIST += $(main_icon_view_sources)
endif

if LIBGD_MAIN_LIST_VIEW
main_list_view_sources =			\
	libgd/gd-main-list-view.c		\
	libgd/gd-main-list-view.h		\
	$(NULL)

nodist_libgd_la_SOURCES += $(main_list_view_sources)
EXTRA_DIST += $(main_list_view_sources)
endif

if LIBGD_MAIN_VIEW
main_view_sources =				\
	libgd/gd-main-view.c			\
	libgd/gd-main-view.h			\
	$(NULL)

nodist_libgd_la_SOURCES += $(main_view_sources)
EXTRA_DIST += $(main_view_sources)
endif

if LIBGD_MARGIN_CONTAINER
margin_container_sources =			\
	libgd/gd-margin-container.c		\
	libgd/gd-margin-container.h		\
	$(NULL)

nodist_libgd_la_SOURCES += $(margin_container_sources)
EXTRA_DIST += $(margin_container_sources)
endif

if LIBGD_NOTIFICATION
notification_sources =				\
	libgd/gd-notification.c			\
	libgd/gd-notification.h			\
	$(NULL)

nodist_libgd_la_SOURCES += $(notification_sources)
EXTRA_DIST += $(notification_sources)
endif

if LIBGD_TAGGED_ENTRY
tagged_entry_sources =				\
	libgd/gd-tagged-entry.c			\
	libgd/gd-tagged-entry.h			\
	$(NULL)

nodist_libgd_la_SOURCES += $(tagged_entry_sources)
EXTRA_DIST += $(tagged_entry_sources)

noinst_PROGRAMS +=				\
	test-tagged-entry			\
	test-tagged-entry-2			\
	$(null)

test_tagged_entry_SOURCES =				\
	test-tagged-entry.c				\
	$(NULL)
test_tagged_entry_LDADD =				\
	$(LIBGD_LIBS)				\
	libgd.la				\
	$(NULL)

test_tagged_entry_2_SOURCES =			\
	test-tagged-entry-2.c			\
	$(NULL)
test_tagged_entry_2_LDADD =			\
	$(LIBGD_LIBS)				\
	libgd.la				\
	$(NULL)
endif

if LIBGD_GIR
include $(INTROSPECTION_MAKEFILE)
INTROSPECTION_GIRS = Gd-1.0.gir

Gd-1.0.gir: libgd.la Makefile
Gd_1_0_gir_NAMESPACE = Gd
Gd_1_0_gir_VERSION = 1.0
Gd_1_0_gir_LIBS = libgd.la
Gd_1_0_gir_CFLAGS = $(AM_CPPFLAGS)
Gd_1_0_gir_SCANNERFLAGS =			\
       --warn-all				\
       --symbol-prefix=gd			\
       --identifier-prefix=Gd			\
        --c-include="libgd/gd.h"	        \
       $(NULL)
Gd_1_0_gir_INCLUDES = $(LIBGD_GIR_INCLUDES)
Gd_1_0_gir_FILES = $(nodist_libgd_la_SOURCES)

if LIBGD_STATIC
noinst_DATA += $(srcdir)/Gd-1.0.gir
EXTRA_DIST += $(srcdir)/Gd-1.0.gir
MAINTAINERCLEANFILES += $(srcdir)/Gd-1.0.gir
else
girdir= $(pkgdatadir)/gir-1.0
typelibdir= $(pkglibdir)/girepository-1.0

gir_DATA = $(INTROSPECTION_GIRS)
typelib_DATA = $(gir_DATA:.gir=.typelib)

CLEANFILES += $(gir_DATA) $(typelib_DATA)
endif
endif

if LIBGD_VAPI
VAPIS = $(srcdir)/gd-1.0.vapi

$(srcdir)/gd-1.0.vapi: $(srcdir)/Gd-1.0.gir
	$(AM_V_GEN)$(VAPIGEN)			\
		--library gd-1.0		\
		--pkg gtk+-3.0			\
		$<
#This 'touch' is a workaround for vapigen not touching the dest file if
#its content hasn't changed, which causes the rule to generate the .vapi
#file to always trigger
	@touch $@

noinst_DATA += $(VAPIS)
EXTRA_DIST += $(VAPIS)
MAINTAINERCLEANFILES += $(VAPIS)
endif
