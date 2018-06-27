# Compiling the resources
VCS_TAG = run_command('git', 'rev-parse', '--short', 'HEAD').stdout().strip()
if VCS_TAG == ''
  if get_option('profile') != 'default'
    VCS_TAG = 'devel'
  else
    VCS_TAG = 'stable'
  endif
endif
about_dialog_conf = configuration_data()
about_dialog_conf.set('PACKAGE_VERSION', '@0@-@1@'.format(meson.project_version(), VCS_TAG))
about_dialog_conf.set('PACKAGE_URL', PACKAGE_URL)
about_dialog_conf.set('PROGRAM_NAME', 'Music' + NAME_SUFFIX)
about_dialog_conf.set('APPID', APPLICATION_ID)

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
appstreamcli = find_program(['appstreamcli', 'appstream-util'], required: false)
if appstreamcli.found()
  test (
    'Validate appdata file',
    appstreamcli,
    args: ['validate', join_paths(meson.current_build_dir (), APPLICATION_ID + '.appdata.xml')]
  )
endif

# Installing the icons
icon_sizes = ['16', '22', '32', '48', '256']

foreach i : icon_sizes
  install_data(
    join_paths('icons/hicolor', i + 'x' + i, 'apps', PROJECT_RDNN_NAME + '.png'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons', 'hicolor', i + 'x' + i, 'apps'),
    rename: '@0@.png'.format(APPLICATION_ID)
  )
endforeach

# Installing the symbolic icon
install_data(
    join_paths('icons/hicolor/symbolic/apps', PROJECT_RDNN_NAME + '-symbolic.svg'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons/hicolor/symbolic/apps'),
    rename: '@0@-symbolic.svg'.format(APPLICATION_ID)
)
