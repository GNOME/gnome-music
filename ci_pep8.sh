#/bin/sh
set -x

cd /mnt

dnf install -y python3-pep8
python3-pep8 --ignore=E501,E225,E265,E402 --show-source --show-pep8 .