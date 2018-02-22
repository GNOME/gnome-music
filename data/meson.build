# Compiling the resources
about_dialog_conf = configuration_data()
about_dialog_conf.set('PACKAGE_VERSION', meson.project_version())
about_dialog_conf.set('PACKAGE_URL', PACKAGE_URL)

gnome.compile_resources(
  PROJECT_RDNN_NAME,
  PROJECT_RDNN_NAME + '.gresource.xml',
  gresource_bundle: true,
  source_dir: '.',
  install_dir: PKGDATA_DIR,
  install: true,
  dependencies: configure_file(
    input: 'AboutDialog.ui.in',
    output: 'AboutDialog.ui',
    configuration: about_dialog_conf
  )
)

# Installing the schema file 
install_data(
  PROJECT_RDNN_NAME + '.gschema.xml',
  install_dir: 'share/glib-2.0/schemas'
)

# Merging the translations with the desktop file
i18n.merge_file(
  output: PROJECT_RDNN_NAME + '.desktop',
  input: PROJECT_RDNN_NAME + '.desktop.in',
  po_dir: join_paths(meson.source_root(), 'po'),
  type: 'desktop',
  install: true,
  install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'applications')
)

# Validating the desktop file
desktop_file_validate = find_program('desktop-file-validate', required:false)
if desktop_file_validate.found()
  test (
    'Validate desktop file',
    desktop_file_validate,
    args: join_paths(meson.current_build_dir (), PROJECT_RDNN_NAME + '.desktop')
  )
endif

# Merging the translations with the appdata file
i18n.merge_file(
  output: PROJECT_RDNN_NAME + '.appdata.xml',
  input: PROJECT_RDNN_NAME + '.appdata.xml.in',
  po_dir: join_paths(meson.source_root(), 'po'),
  install: true,
  install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'metainfo')
)

# Validating the appdata file
appstreamcli = find_program(['appstreamcli', 'appstream-util'], required: false)
if appstreamcli.found()
  test (
    'Validate appdata file',
    appstreamcli,
    args: ['validate', join_paths(meson.current_build_dir (), PROJECT_RDNN_NAME + '.appdata.xml')]
  )
endif

# Installing the icons
icon_sizes = ['16', '22', '32', '48', '256']

foreach i : icon_sizes
  install_data(
    join_paths('icons/hicolor', i + 'x' + i, 'apps', PROJECT_RDNN_NAME + '.png'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons', 'hicolor', i + 'x' + i, 'apps')
  )
endforeach

# Installing the symbolic icon
install_data(
    join_paths('icons/hicolor/symbolic/apps', PROJECT_RDNN_NAME + '-symbolic.svg'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons/hicolor/symbolic/apps')
)