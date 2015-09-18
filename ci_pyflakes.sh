#/bin/sh
set -x

cd /mnt

dnf install -y python3-pyflakes
python3-pyflakes .