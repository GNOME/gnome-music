# AboutDialog.ui configuration
VCS_TAG = ''
if get_option('profile') != 'default'
  git = find_program('git', required : false)
  if git.found()
    VCS_TAG = run_command('git', 'rev-parse', '--short', 'HEAD').stdout().strip()
  endif
  if VCS_TAG == ''
    VCS_TAG = '-devel'
  else
    VCS_TAG = '-@0@'.format(VCS_TAG)
  endif
endif
about_dialog_conf = configuration_data()
about_dialog_conf.set('PACKAGE_VERSION', '@0@@1@'.format(meson.project_version(), VCS_TAG))
about_dialog_conf.set('PACKAGE_URL', PACKAGE_URL)
about_dialog_conf.set('PROGRAM_NAME', 'Music' + NAME_SUFFIX)
about_dialog_conf.set('APPID', APPLICATION_ID)

about_dialog = configure_file(
    input: 'AboutDialog.ui.in',
    output: 'AboutDialog.ui',
    configuration: about_dialog_conf
  )