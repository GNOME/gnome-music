#!/bin/sh
mkdir -p m4
autopoint --force
AUTOPOINT='intltoolize --automake --copy' autoreconf -fiv -Wall || exit
./configure --enable-maintainer-mode "$@"
