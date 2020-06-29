# Files needed for running Tracker inside the Flatpak sandbox, for systems
# which don't have a suitable version of Tracker in the host OS.
#
# We must export the .service files from the sandbox so they work on the
# session bus. This means the Tracker domain name must correspond with the
# application ID.

domain_ontologies_dir = get_option('datadir') / 'tracker3' / 'domain-ontologies'
dbus_services_dir = get_option('datadir') / 'dbus-1' / 'services'

tracker_domain_config = configuration_data()
tracker_domain_config.set('application_id', APPLICATION_ID)
tracker_domain_config.set('domain_rule', get_option('prefix') / domain_ontologies_dir / APPLICATION_ID + '.domain.rule')

configure_file(
  input: 'org.gnome.Music.domain.rule.in',
  output: APPLICATION_ID + '.domain.rule',
  configuration: tracker_domain_config,
  install_dir: domain_ontologies_dir)

configure_file(
  input: 'org.gnome.Music.Tracker3.Miner.Extract.service.in',
  output: APPLICATION_ID + '.Tracker3.Miner.Extract.service',
  configuration: tracker_domain_config,
  install_dir: dbus_services_dir)

configure_file(
  input: 'org.gnome.Music.Tracker3.Miner.Files.service.in',
  output: APPLICATION_ID + '.Tracker3.Miner.Files.service',
  configuration: tracker_domain_config,
  install_dir: dbus_services_dir)
