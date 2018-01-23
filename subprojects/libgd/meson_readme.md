See README for general information. Read below for usage with Meson.

Usage
=====

libgd is intended to be used as a submodule from other projects. This requires passing default_options to the subproject
which was added in Meson 0.38.0. To see a full list of options you can run `mesonconf $your_build_dir`. If building a
non-static library `pkglibdir` must be set to a private location to install to which you will also want to pass (an absolute path)
with the `install_rpath` keyword to any executables. For introspection files you also must set `pkgdatadir`.

So given a Meson project using git you would run this to do initial setup:

```
mkdir subprojects
git submodule add https://git.gnome.org/browse/libgd subprojects/libgd
```

Then from within your `meson.build` file:

Static Library
--------------

```meson
libgd = subproject('libgd',
  default_options: [
    'with-tagged-entry=true'
  ]
)
# Pass as dependency to another target
libgd_dep = libgd.get_variable('libgd_dep')
```

```c
#include "libgd/gd.h"

int main(int argc, char **argv)
{
  gd_ensure_types(); /* As a test */
  return 0;
}
```

Introspection
-------------

```meson
pkglibdir = join_paths(get_option('libdir'), meson.project_name())
pkgdatadir = join_paths(get_option('datadir'), meson.project_name())
libgd = subproject('libgd',
  default_options: [
    'pkglibdir=' + pkglibdir,
    'pkgdatadir=' + pkgdatadir,
    'with-tagged-entry=true',
    'with-introspection=true',
    'static=false',
  ]
)
```

```python
import os
import gi
gi.require_version('GIRepository', '2.0')
from gi.repository import GIRepository
pkglibdir = '/usr/lib/foo' # This would be defined at build time
pkggirdir = os.path.join(pkglibdir, 'girepository-1.0')
GIRepository.Repository.prepend_search_path(pkggirdir)
GIRepository.Repository.prepend_library_path(pkglibdir)
gi.require_version('Gd', '1.0')
```

Vala
----

```meson
pkglibdir = join_paths(get_option('libdir'), meson.project_name())
libgd = subproject('libgd',
  default_options: [
    'pkglibdir=' + pkglibdir,
    'with-tagged-entry=true',
    'with-vapi=true'
  ]
)
# Pass as dependency to a Vala target
libgd_vapi_dep = libgd.get_variable('libgd_vapi_dep')
```

<!-- TODO: Make a Vala example -->
