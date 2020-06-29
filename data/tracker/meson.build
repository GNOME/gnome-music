# Files needed for running Tracker inside the Flatpak sandbox.

domain_ontologies_dir = get_option('datadir') / 'tracker3' / 'domain-ontologies'
dbus_services_dir = get_option('datadir') / 'dbus-1' / 'services'

install_data('org.gnome.Music.domain.rule', install_dir: domain_ontologies_dir)
install_data('org.gnome.Music.Miner.Extract.service', install_dir: dbus_services_dir)
install_data('org.gnome.Music.Miner.Files.service', install_dir: dbus_services_dir)
