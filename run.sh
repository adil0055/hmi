#!/usr/bin/env bash
# Launch the cluster and its test panel.
#
#   ./run.sh                 cluster + control panel
#   ./run.sh --no-panel      cluster only
#   ./run.sh --fullscreen    cluster full screen (F11 toggles, Esc leaves)
#
# Creates a local virtualenv on first run so nothing is installed system-wide.
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
if [ ! -d "$VENV" ]; then
    echo "Creating virtualenv in $VENV ..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet -r requirements.txt
fi

exec "$VENV/bin/python" main.py "$@"
