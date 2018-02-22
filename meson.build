project('gnome-music',
    version: '3.27.90'
)

# Importing modules
gnome = import('gnome')
i18n  = import('i18n')
python = import('python3')

# Make sure Python is installed and found
if not python.find_python().found()
    error('No valid python3 binary found')
endif

# Constants
PACKAGE_URL = 'https://wiki.gnome.org/Apps/Music'
PACKAGE_URL_BUG = 'https://gitlab.gnome.org/GNOME/gnome-music'
PROJECT_RDNN_NAME='org.gnome.Music'

PYTHON_DIR = join_paths(get_option('prefix'), python.sysconfig_path('purelib'))
PKGDATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), PROJECT_RDNN_NAME)
PKGLIB_DIR = join_paths(PKGDATA_DIR, 'libs')
# Dependencies 
dependency('gobject-introspection-1.0', version: '>= 1.35.0')
dependency('gtk+-3.0', version: '>= 3.19.3')
dependency('libmediaart-2.0', version: '>= 1.9.1')
dependency('tracker-sparql-2.0', version: '>= 1.99.1')
dependency('pygobject-3.0', version: '>= 3.21.1')
dependency('py3cairo', version: '>= 1.14.0')
dependency('grilo-0.3', version: '>= 0.3.4')


subproject('libgd',
    default_options: [
        'with-introspection=true',
        'with-main-view=true',
        'with-tagged-entry=true',
        'with-gtk-hacks=true',
        'static=false',
        'pkgdatadir=' + PKGDATA_DIR,
        'pkglibdir=' + PKGLIB_DIR
    ])

subdir('data')
subdir('help')
subdir('po')

install_subdir(
    'gnomemusic',
    install_dir: PYTHON_DIR
)


# Install the executable file
bin_config = configuration_data()
bin_config.set('pkgdatadir', PKGDATA_DIR)
bin_config.set('localedir', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
bin_config.set('pythondir', PYTHON_DIR)
bin_config.set('pyexecdir', join_paths(get_option('prefix'), python.sysconfig_path('stdlib')))
# Used for libgd
bin_config.set('pkglibdir', PKGLIB_DIR)

configure_file(
    input: 'gnome-music.in',
    output: 'gnome-music',
    configuration: bin_config,
    install_dir: get_option('bindir')
)

meson.add_postconf_script('meson_post_conf.py')

# Run the post install script
meson.add_install_script('meson_post_install.py')