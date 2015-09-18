#/bin/sh
set -x

dnf install -y gnome-common make which intltool python3 \
    gobject-introspection-devel gtk3-devel libmediaart-devel grilo-devel git
git submodule update --init
/mnt/autogen.sh
make

if [ $(git describe --exact-match HEAD) ]; then
    echo "Its a tag!"
    make distcheck
fi