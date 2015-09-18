#/bin/sh
set -x

dnf install -y gnome-common make which intltool
/mnt/autogen.sh
#make
