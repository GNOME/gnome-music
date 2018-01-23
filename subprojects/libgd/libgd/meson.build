gnome = import('gnome')

sources = [
  'gd.h',
  'gd-types-catalog.c'
]
built_sources = []
c_args = []
private_c_args = [
  '-DG_LOG_DOMAIN="libgd"',
  '-DG_DISABLE_DEPRECATED',
]

if get_option('with-gtk-hacks')
  sources += [
    'gd-icon-utils.c',
    'gd-icon-utils.h',
  ]
  c_args += '-DLIBGD_GTK_HACKS=1'
endif

if (get_option('with-main-box') or
    get_option('with-main-icon-box'))
  sources += [
    'gd-main-box-child.c',
    'gd-main-box-child.h',
    'gd-main-box-generic.c',
    'gd-main-box-generic.h',
    'gd-main-box-item.c',
    'gd-main-box-item.h'
  ]
  c_args += '-DLIBGD__BOX_COMMON=1'

  if get_option('with-main-icon-box')
    sources += [
      'gd-main-icon-box.c',
      'gd-main-icon-box.h',
      'gd-main-icon-box-child.c',
      'gd-main-icon-box-child.h',
      'gd-main-icon-box-icon.c',
      'gd-main-icon-box-icon.h',
      'gd-icon-utils.c',
      'gd-icon-utils.h',
    ]
    c_args += '-DLIBGD_MAIN_ICON_BOX=1'
  endif

  if get_option('with-main-box')
    sources += [
      'gd-main-box.c',
      'gd-main-box.h',
    ]
    c_args += '-DLIBGD_MAIN_BOX=1'
  endif
endif

if (get_option('with-main-icon-view') or
    get_option('with-main-list-view') or
    get_option('with-main-view'))
  sources += [
    'gd-main-view-generic.c',
    'gd-main-view-generic.h',
    'gd-styled-text-renderer.c',
    'gd-styled-text-renderer.h',
    'gd-two-lines-renderer.c',
    'gd-two-lines-renderer.h',
  ]
  c_args += '-DLIBGD__VIEW_COMMON=1'

  if (get_option('with-main-icon-view') or
      get_option('with-main-view'))
    sources += [
      'gd-main-icon-view.c',
      'gd-main-icon-view.h',
      'gd-toggle-pixbuf-renderer.c',
      'gd-toggle-pixbuf-renderer.h'
    ]
    c_args += '-DLIBGD_MAIN_ICON_VIEW=1'
  endif

  if (get_option('with-main-list-view') or
      get_option('with-main-view'))
    sources += [
      'gd-main-list-view.c',
      'gd-main-list-view.h',
    ]
    c_args += '-DLIBGD_MAIN_LIST_VIEW=1'
  endif

  if get_option('with-main-view')
    sources += [
      'gd-main-view.c',
      'gd-main-view.h',
    ]
    c_args += '-DLIBGD_MAIN_VIEW=1'
  endif
endif

if get_option('with-margin-container')
  sources += [
    'gd-margin-container.c',
    'gd-margin-container.h',
  ]
  c_args += '-DLIBGD_MARGIN_CONTAINER=1'
endif

if get_option('with-tagged-entry')
  sources += [
    'gd-tagged-entry.c',
    'gd-tagged-entry.h',
  ]
  c_args += '-DLIBGD_TAGGED_ENTRY=1'
endif

if get_option('with-notification')
  sources += [
    'gd-notification.c',
    'gd-notification.h',
  ]
  c_args += '-DLIBGD_NOTIFICATION=1'
endif

if sources.length() == 2
  error('You must include a feature to be built!')
endif

# --------- Building -----------

static = get_option('static')
install_introspection = get_option('with-introspection')
with_vapi = get_option('with-vapi')

if static
  libgd_lib = static_library('gd', sources,
    dependencies: [libgtk, libm],
    include_directories: libgd_include,
    c_args: c_args + private_c_args
  )
endif

# Currently in Meson building gir requires a shared library
if not static or (install_introspection or with_vapi)
  if not static and pkglibdir == ''
    error('Installing shared library but pkglibdir is unset!')
  endif

  libgd_shared_lib = shared_library('gd', sources,
    dependencies: [libgtk, libm],
    include_directories: libgd_include,
    c_args: c_args + private_c_args,
    install: not static,
    install_dir: pkglibdir
  )

  if not static
    libgd_lib = libgd_shared_lib
  endif
endif

if install_introspection or with_vapi
  if install_introspection
    if pkgdatadir == ''
      error('Installing introspection but pkgdatadir is unset!')
    elif pkglibdir == ''
      error('Installing introspection but pkglibdir is unset!')
    endif
  endif

  libgd_gir = gnome.generate_gir(libgd_shared_lib,
    sources : sources,
    nsversion : '1.0',
    namespace : 'Gd',
    symbol_prefix : 'gd',
    identifier_prefix : 'Gd',
    includes : 'Gtk-3.0',
    include_directories: libgd_include,
    install: install_introspection,
    install_dir_gir: join_paths(pkgdatadir, 'gir-1.0'),
    install_dir_typelib: join_paths(pkglibdir, 'girepository-1.0'),
    extra_args: [
      '--c-include=libgd/gd.h',
    ]
  )
  built_sources += libgd_gir

  if get_option('with-vapi')
    libgd_vapi_dep = gnome.generate_vapi('gd-1.0',
      sources: libgd_gir[0],
      packages: ['gtk+-3.0']
    )
  endif
endif

libgd_dep = declare_dependency(
  link_with: libgd_lib,
  include_directories: libgd_include,
  dependencies: libgtk,
  compile_args: c_args,
  sources: built_sources
)
