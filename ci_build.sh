#/bin/sh
set -x

cd /mnt

# Dependencies
dnf install -y python3 gobject-introspection-devel gtk3-devel \
               libmediaart-devel grilo-devel

# Other boring stuff
dnf install -y gnome-common make which intltool git xz

git submodule update --init
./autogen.sh

if [ $(git describe --exact-match HEAD) ]; then
    echo "New release"
    make distcheck
else
    make
fi