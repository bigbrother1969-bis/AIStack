#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# Scheduled restore tests (2.0): run on the host by aistack-pra.timer.
# Same declarations as the web container — `./config` when it exists —
# like run_dock.sh.
if [ -d "$AISTACK_REPO_ROOT/config" ]; then
    export AISTACK_CONFIG_DIR="$AISTACK_REPO_ROOT/config"
fi
cd "$AISTACK_REPO_ROOT"
exec "$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.pra_schedule "$@"
