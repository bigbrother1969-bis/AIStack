#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# The dock executor (ADR-0019): run on the host by aistack-dock.timer.
# It reads the same declarations as the web container — `./config`
# when it exists (the container's /config), else the shipped ones — so
# the proposals the page records and the service the dock changes are
# declared once.
if [ -d "$AISTACK_REPO_ROOT/config" ]; then
    export AISTACK_CONFIG_DIR="$AISTACK_REPO_ROOT/config"
fi
cd "$AISTACK_REPO_ROOT"
exec "$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.dock "${@:-run}"
