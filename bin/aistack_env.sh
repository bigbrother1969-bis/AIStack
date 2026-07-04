#!/usr/bin/env bash
set -euo pipefail

export AISTACK_REPO_ROOT="/srv/aistack/AISTack"
export PYTHONPATH="$AISTACK_REPO_ROOT:${PYTHONPATH:-}"

cd "$AISTACK_REPO_ROOT"
