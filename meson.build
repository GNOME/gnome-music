project('gnome-music',
    version: '3.35.3',
    meson_version: '>= 0.46.0'
)

# Importing modules
gnome = import('gnome')
i18n  = import('i18n')
python = import('python')

# Module objects
py_installation = python.find_installation('python3')

# Make sure Python is installed and found
if not py_installation.found()
    error('No valid python3 binary found')
endif

# Constants
PACKAGE_URL = 'https://wiki.gnome.org/Apps/Music'
PACKAGE_URL_BUG = 'https://gitlab.gnome.org/GNOME/gnome-music/issues'
PROJECT_RDNN_NAME = 'org.gnome.Music'

# NAME_SUFFIX is used in the about dialog
if get_option('profile') == 'development'
  PROFILE = '.Devel'
  NAME_SUFFIX = ' (Development Snapshot)'
else
  PROFILE = ''
  NAME_SUFFIX = ''
endif

APPLICATION_ID = 'org.gnome.Music@0@'.format(PROFILE)
PYTHON_DIR = py_installation.get_path('purelib')
PKGDATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), APPLICATION_ID)
PKGLIB_DIR = join_paths(get_option('prefix'), get_option('libdir'), APPLICATION_ID)

# Dependencies
dependency('goa-1.0')
dependency('gobject-introspection-1.0', version: '>= 1.35.0')
dependency('gtk+-3.0', version: '>= 3.24.7')
dependency('libdazzle-1.0', version: '>= 3.28.0')
dependency('libmediaart-2.0', version: '>= 1.9.1')
dependency('libsoup-2.4')
dependency('tracker-sparql-2.0', version: '>= 2.3.0')
dependency('pygobject-3.0', version: '>= 3.29.1')
dependency('py3cairo', version: '>= 1.14.0')
dependency('grilo-0.3', version: '>= 0.3.9', fallback: ['grilo', 'libgrl_dep'])
dependency('grilo-plugins-0.3', version: '>= 0.3.10', fallback: ['grilo-plugins', 'grilo_plugins_dep'])

subproject('libgd',
    default_options: [
        'with-introspection=true',
        'with-main-view=true',
        'with-tagged-entry=true',
        'static=false',
        'pkgdatadir=' + PKGDATA_DIR,
        'pkglibdir=' + PKGLIB_DIR
    ])

subproject('gfm',
    default_options: [
        'pkgdatadir=' + PKGDATA_DIR,
        'pkglibdir=' + PKGLIB_DIR
    ])

subdir('data/ui')
subdir('data')
subdir('help')
subdir('po')

install_subdir(
    'gnomemusic',
    install_dir: py_installation.get_install_dir()
)

# Install the executable file
bin_config = configuration_data()
bin_config.set('application_id', APPLICATION_ID)
bin_config.set('rdnn_name', PROJECT_RDNN_NAME)
bin_config.set('pkgdatadir', PKGDATA_DIR)
bin_config.set('localedir', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
bin_config.set('pythondir', PYTHON_DIR)
bin_config.set('pyexecdir', py_installation.get_path('stdlib'))
bin_config.set('schemasdir', PKGDATA_DIR)
# Used for libgd/gfm
bin_config.set('pkglibdir', PKGLIB_DIR)
bin_config.set('gfmlibdir', PKGLIB_DIR)

bin_config.set('local_build', 'False')

configure_file(
    input: 'gnome-music.in',
    output: 'gnome-music',
    configuration: bin_config,
    install_dir: get_option('bindir')
)

# Install the builddir executable
local_config = configuration_data()
local_config.set('application_id', APPLICATION_ID)
local_config.set('rdnn_name', PROJECT_RDNN_NAME)
local_config.set('pkgdatadir', join_paths(meson.build_root(), 'data'))
local_config.set('localedir', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
local_config.set('pythondir', meson.source_root())
local_config.set('pyexecdir', meson.source_root())
local_config.set('schemasdir', join_paths(meson.build_root(), 'data'))
# Used for libgd/gfm
local_config.set('pkglibdir', join_paths(meson.build_root(), 'subprojects', 'libgd', 'libgd'))
local_config.set('gfmlibdir', join_paths(meson.build_root(), 'subprojects', 'gfm'))

local_config.set('local_build', 'True')

configure_file(
    input: 'gnome-music.in',
    output: 'local-music',
    configuration: local_config
)

meson.add_postconf_script('meson_post_conf.py')
meson.add_install_script('meson_post_install.py')
