dnl The option stuff below is based on the similar code from Automake

# _LIBGD_MANGLE_OPTION(NAME)
# -------------------------
# Convert NAME to a valid m4 identifier, by replacing invalid characters
# with underscores, and prepend the _LIBGD_OPTION_ suffix to it.
AC_DEFUN([_LIBGD_MANGLE_OPTION],
[[_LIBGD_OPTION_]m4_bpatsubst($1, [[^a-zA-Z0-9_]], [_])])

# _LIBGD_SET_OPTION(NAME)
# ----------------------
# Set option NAME.  If NAME begins with a digit, treat it as a requested
# Guile version number, and define _LIBGD_GUILE_VERSION to that number.
# Otherwise, define the option using _LIBGD_MANGLE_OPTION.
AC_DEFUN([_LIBGD_SET_OPTION],
[m4_define(_LIBGD_MANGLE_OPTION([$1]), 1)])

# _LIBGD_SET_OPTIONS(OPTIONS)
# ----------------------------------
# OPTIONS is a space-separated list of libgd options.
AC_DEFUN([_LIBGD_SET_OPTIONS],
[m4_foreach_w([_LIBGD_Option], [$1], [_LIBGD_SET_OPTION(_LIBGD_Option)])])

# _LIBGD_IF_OPTION_SET(NAME,IF-SET,IF-NOT-SET)
# -------------------------------------------
# Check if option NAME is set.
AC_DEFUN([_LIBGD_IF_OPTION_SET],
[m4_ifset(_LIBGD_MANGLE_OPTION([$1]),[$2],[$3])])

dnl LIBGD_INIT([OPTIONS], [DIR])
dnl ----------------------------
dnl OPTIONS      A whitespace-seperated list of options.
dnl DIR          libgd submodule directory (defaults to 'libgd')
AC_DEFUN([LIBGD_INIT], [
    _LIBGD_SET_OPTIONS([$1])
    AC_SUBST([LIBGD_MODULE_DIR],[m4_if([$2],,[libgd],[$2])])

    AC_REQUIRE([LT_INIT])
    AC_REQUIRE([AC_CHECK_LIBM])
    AC_SUBST(LIBM)
    LIBGD_MODULES="gtk+-3.0 >= 3.7.10"
    LIBGD_GIR_INCLUDES="Gtk-3.0"
    LIBGD_SOURCES=""

    AM_CONDITIONAL([LIBGD_STATIC],[_LIBGD_IF_OPTION_SET([static],[true],[false])])

    # main-box:
    AM_CONDITIONAL([LIBGD_MAIN_BOX],[_LIBGD_IF_OPTION_SET([main-box],[true],[false])])
    _LIBGD_IF_OPTION_SET([main-box],[
        _LIBGD_SET_OPTION([main-icon-box])
        AC_DEFINE([LIBGD_MAIN_BOX], [1], [Description])
    ])

    # main-icon-box:
    AM_CONDITIONAL([LIBGD_MAIN_ICON_BOX],[_LIBGD_IF_OPTION_SET([main-icon-box],[true],[false])])
    _LIBGD_IF_OPTION_SET([main-icon-box],[
        _LIBGD_SET_OPTION([_box-common])
        _LIBGD_SET_OPTION([gtk-hacks])
        AC_DEFINE([LIBGD_MAIN_ICON_BOX], [1], [Description])
    ])

    # main-view:
    AM_CONDITIONAL([LIBGD_MAIN_VIEW],[_LIBGD_IF_OPTION_SET([main-view],[true],[false])])
    _LIBGD_IF_OPTION_SET([main-view],[
        _LIBGD_SET_OPTION([main-icon-view])
        _LIBGD_SET_OPTION([main-list-view])
        _LIBGD_SET_OPTION([gtk-hacks])
        AC_DEFINE([LIBGD_MAIN_VIEW], [1], [Description])
    ])

    # main-icon-view:
    AM_CONDITIONAL([LIBGD_MAIN_ICON_VIEW],[_LIBGD_IF_OPTION_SET([main-icon-view],[true],[false])])
    _LIBGD_IF_OPTION_SET([main-icon-view],[
        _LIBGD_SET_OPTION([_view-common])
        AC_DEFINE([LIBGD_MAIN_ICON_VIEW], [1], [Description])
    ])

    # main-list-view:
    AM_CONDITIONAL([LIBGD_MAIN_LIST_VIEW],[_LIBGD_IF_OPTION_SET([main-list-view],[true],[false])])
    _LIBGD_IF_OPTION_SET([main-list-view],[
        _LIBGD_SET_OPTION([_view-common])
        AC_DEFINE([LIBGD_MAIN_LIST_VIEW], [1], [Description])
    ])

    # margin-container:
    AM_CONDITIONAL([LIBGD_MARGIN_CONTAINER],[_LIBGD_IF_OPTION_SET([margin-container],[true],[false])])
    _LIBGD_IF_OPTION_SET([margin-container],[
        AC_DEFINE([LIBGD_MARGIN_CONTAINER], [1], [Description])
    ])

    # notification:
    AM_CONDITIONAL([LIBGD_NOTIFICATION],[_LIBGD_IF_OPTION_SET([notification],[true],[false])])
    _LIBGD_IF_OPTION_SET([notification],[
        AC_DEFINE([LIBGD_NOTIFICATION], [1], [Description])
    ])

    # tagged-entry: Gtk+ widget
    AM_CONDITIONAL([LIBGD_TAGGED_ENTRY],[_LIBGD_IF_OPTION_SET([tagged-entry],[true],[false])])
    _LIBGD_IF_OPTION_SET([tagged-entry],[
        AC_DEFINE([LIBGD_TAGGED_ENTRY], [1], [Description])
    ])

    # vapi: vala bindings support
    AM_CONDITIONAL([LIBGD_VAPI],[ _LIBGD_IF_OPTION_SET([vapi],[true],[false])])
    _LIBGD_IF_OPTION_SET([vapi],[
        _LIBGD_SET_OPTION([gir])
        dnl check for vapigen
        AC_PATH_PROG(VAPIGEN, vapigen, no)
        AS_IF([test x$VAPIGEN = "xno"],
              [AC_MSG_ERROR([Cannot find the "vapigen compiler in your PATH])])
    ])

    # gir: gobject introspection support
    AM_CONDITIONAL([LIBGD_GIR],[ _LIBGD_IF_OPTION_SET([gir],[true],[false])])
    _LIBGD_IF_OPTION_SET([gir],[
        GOBJECT_INTROSPECTION_REQUIRE([0.9.6])
    ])

    # gtk-hacks: collection of Gtk+ hacks and workarounds
    AM_CONDITIONAL([LIBGD_GTK_HACKS],[_LIBGD_IF_OPTION_SET([gtk-hacks],[true],[false])])
    _LIBGD_IF_OPTION_SET([gtk-hacks],[
        AC_DEFINE([LIBGD_GTK_HACKS], [1], [Description])
    ])

    # _box-common:
    AM_CONDITIONAL([LIBGD__BOX_COMMON],[_LIBGD_IF_OPTION_SET([_box-common],[true],[false])])
    _LIBGD_IF_OPTION_SET([_box-common],[
        AC_DEFINE([LIBGD__BOX_COMMON], [1], [Description])
    ])

    # _view-common:
    AM_CONDITIONAL([LIBGD__VIEW_COMMON],[_LIBGD_IF_OPTION_SET([_view-common],[true],[false])])
    _LIBGD_IF_OPTION_SET([_view-common],[
        AC_DEFINE([LIBGD__VIEW_COMMON], [1], [Description])
    ])

    PKG_CHECK_MODULES(LIBGD, [ $LIBGD_MODULES ])
    AC_SUBST(LIBGD_GIR_INCLUDES)
    AC_SUBST(LIBGD_SOURCES)
])
