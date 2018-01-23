#!/usr/bin/env python3

import os
import subprocess

prefix = os.environ.get('MESON_INSTALL_PREFIX', '/usr/local')
datadir = os.path.join(prefix, 'share')

# Packaging tools define DESTDIR and this isn't needed for them
if 'DESTDIR' not in os.environ:
    print('Updating icon cache...')
    icon_cache_dir = os.path.join(datadir, 'icons', 'hicolor')
    subprocess.call(['gtk-update-icon-cache', '-qtf', icon_cache_dir])

    print("Compiling the schema...")
    schemas_dir = os.path.join(datadir, 'glib-2.0/schemas')
    subprocess.call(['glib-compile-schemas', schemas_dir])

    print('Updating desktop database...')
    desktop_database_dir = os.path.join(datadir, 'applications')
    subprocess.call(['update-desktop-database', '-q', desktop_database_dir])
