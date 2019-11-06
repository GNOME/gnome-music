# Compiling the resources
# about_dialog is defined in data/ui/meson.build to generate the output file in that directory
gnome.compile_resources(
  PROJECT_RDNN_NAME,
  PROJECT_RDNN_NAME + '.gresource.xml',
  gresource_bundle: true,
  source_dir: meson.current_build_dir(),
  install_dir: PKGDATA_DIR,
  install: true,
  dependencies: about_dialog
)

# Installing the schema file
install_data(
  PROJECT_RDNN_NAME + '.gschema.xml',
  install_dir: 'share/glib-2.0/schemas'
)

# Merging the translations with the desktop file
desktop_conf = configuration_data()
desktop_conf.set('icon', APPLICATION_ID)
i18n.merge_file(
  type: 'desktop',
  input: configure_file(
    output: PROJECT_RDNN_NAME + '.desktop.in',
    input: PROJECT_RDNN_NAME + '.desktop.in.in',
    configuration: desktop_conf),
  output: APPLICATION_ID + '.desktop',
  po_dir: join_paths(meson.source_root(), 'po'),
  install: true,
  install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'applications')
)

# Validating the desktop file
desktop_file_validate = find_program('desktop-file-validate', required:false)
if desktop_file_validate.found()
  test (
    'Validate desktop file',
    desktop_file_validate,
    args: join_paths(meson.current_build_dir (), APPLICATION_ID + '.desktop')
  )
endif

# Merging the translations with the appdata file
appdata_conf = configuration_data()
appdata_conf.set('appid', APPLICATION_ID)
appdata_conf.set('package_url', PACKAGE_URL)
appdata_conf.set('package_url_bug', PACKAGE_URL_BUG)
i18n.merge_file(
  'appdata',
  input: configure_file(
    output: PROJECT_RDNN_NAME + '.appdata.xml.in',
    input: PROJECT_RDNN_NAME + '.appdata.xml.in.in',
    configuration: appdata_conf
  ),
  output: APPLICATION_ID + '.appdata.xml',
  po_dir: join_paths(meson.source_root(), 'po'),
  install: true,
  install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'metainfo')
)

# Validating the appdata file
appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test (
    'Validate appdata file',
    appstream_util,
    args: ['validate-relax', join_paths(meson.current_build_dir (), APPLICATION_ID + '.appdata.xml')]
  )
endif

# Installing the icons
icon_sizes = ['scalable']

foreach i : icon_sizes
  install_data(
    join_paths('icons/hicolor', i , 'apps', APPLICATION_ID + '.svg'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons', 'hicolor', i , 'apps')
  )
endforeach

# Installing the symbolic icon
install_data(
    join_paths('icons/hicolor/symbolic/apps', PROJECT_RDNN_NAME + '-symbolic.svg'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons/hicolor/symbolic/apps'),
    rename: '@0@-symbolic.svg'.format(APPLICATION_ID)
)
