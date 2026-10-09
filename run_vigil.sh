#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# The vigil (2.0), for a git installation: aistack-vigil.service. The
# Gotify address and token come from .env.web, like the web service's
# secrets; same declarations as the web service.
if [ -d "$AISTACK_REPO_ROOT/config" ]; then
    export AISTACK_CONFIG_DIR="$AISTACK_REPO_ROOT/config"
fi
if [ -f "$AISTACK_REPO_ROOT/.env.web" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$AISTACK_REPO_ROOT/.env.web"
    set +a
fi
cd "$AISTACK_REPO_ROOT"
exec "$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.vigil "$@"
