#!/bin/bash

set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
INSTALL_DIR=/opt/petfeeder

apt-get install -y python3-pip python3-venv

python3 -m venv "${INSTALL_DIR}/venv"
source "${INSTALL_DIR}/venv/bin/activate"

cd "${INSTALL_DIR}"
echo "Installing python requirements"
python -m pip install -r requirements.txt

sed "s@{{INSTALL_DIR}}@${INSTALL_DIR}@g" "${DIR}/petfeeder.service" > /etc/systemd/system/petfeeder.service

systemctl daemon-reload
