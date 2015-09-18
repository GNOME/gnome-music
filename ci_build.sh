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

if [ -z "$RELEASE" ]; then
    make
else
    echo "New release: $RELEASE"
    make distcheck
    FILENAME=gnome-music-$RELEASE.tar.xz
    echo "Filename: $FILENAME"
    mkdir -p /root/.ssh
    cat << EOF >> /root/.ssh/config
    Host *.gnome.org
        User $SSH_USER
        Compression yes
        CompressionLevel 3
        ControlPersist 5m
        StrictHostKeyChecking no
        IdentityFile /ssh/id_rsa

    ControlMaster auto
    ControlPath /tmp/%r@%h:%p
    ControlPersist yes
EOF
    scp -vvvvv $FILENAME master.gnome.org
    #ssh -t master.gnome.org "ftpadmin install gnome-music-$RELEASE.tar.xz"
fi