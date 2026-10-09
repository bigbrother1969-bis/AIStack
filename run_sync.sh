#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# The generalized sync's executor (ADR-0022 § 6): run on the host by
# aistack-sync.timer. Same declarations as the web container.
if [ -d "$AISTACK_REPO_ROOT/config" ]; then
    export AISTACK_CONFIG_DIR="$AISTACK_REPO_ROOT/config"
fi
cd "$AISTACK_REPO_ROOT"
exec "$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.sync_apply "$@"
