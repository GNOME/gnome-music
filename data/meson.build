# Compiling the resources
# about_dialog is defined in data/ui/meson.build to generate the output file in that directory
gnome.compile_resources(
  PROJECT_RDNN_NAME,
  PROJECT_RDNN_NAME + '.gresource.xml',
  gresource_bundle: true,
  source_dir: meson.current_build_dir(),
  install_dir: PKGDATA_DIR,
  install: true
)

schema_src = PROJECT_RDNN_NAME + '.gschema.xml'
gnome.compile_schemas(build_by_default: true, depend_files: files(schema_src))

# Installing the schema file
install_data(
  schema_src,
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
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
  po_dir: join_paths(meson.project_source_root(), 'po'),
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
appdata_file = i18n.merge_file(
  input: configure_file(
    output: PROJECT_RDNN_NAME + '.metainfo.xml.in',
    input: PROJECT_RDNN_NAME + '.metainfo.xml.in.in',
    configuration: appdata_conf
  ),
  output: APPLICATION_ID + '.metainfo.xml',
  po_dir: join_paths(meson.project_source_root(), 'po'),
  install: true,
  install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'metainfo')
)

# Validating the appdata file
appstreamcli = find_program('appstreamcli', required: false)
if (appstreamcli.found())
  test('Validate appdata file',
    appstreamcli,
    args: ['validate', '--no-net', '--explain', appdata_file],
    workdir: meson.current_build_dir()
  )
endif

# Installing the default icon
install_data(
    join_paths('icons/hicolor/scalable/apps', APPLICATION_ID + '.svg'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons/hicolor/scalable/apps')
)

# Installing the symbolic icon
install_data(
    join_paths('icons/hicolor/symbolic/apps', PROJECT_RDNN_NAME + '-symbolic.svg'),
    install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'icons/hicolor/symbolic/apps'),
    rename: '@0@-symbolic.svg'.format(APPLICATION_ID)
)

# Installing the D-Bus service file
service_conf = configuration_data()
service_conf.set('appid', APPLICATION_ID)
service_conf.set('bindir', join_paths(get_option('prefix'), get_option('bindir')))
configure_file(
  input: PROJECT_RDNN_NAME + '.service.in',
  output: APPLICATION_ID + '.service',
  configuration: service_conf,
  install: true,
  install_dir: join_paths(get_option('prefix'), get_option('datadir'), 'dbus-1', 'services')
)
