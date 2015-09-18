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

RELEASE=$(git describe --exact-match HEAD)

if [ ! -z "$RELEASE" ]; then
    make
else
    echo "New release: $RELEASE"
    make distcheck
    FILENAME=gnome-music-$RELEASE.tar.xz
    #scp $FILENAME master.gnome.org
    #ssh -t master.gnome.org "ftpadmin install gnome-music-$RELEASE.tar.xz"
fi