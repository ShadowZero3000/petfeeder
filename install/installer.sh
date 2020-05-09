#!/bin/bash

set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cp "${DIR}/petfeeder.service" /etc/systemd/system/petfeeder.service
