#!/usr/bin/env bash
set -euo pipefail

export AISTACK_REPO_ROOT="/srv/aistack/AISTack"
export PYTHONPATH="$AISTACK_REPO_ROOT:${PYTHONPATH:-}"

cd "$AISTACK_REPO_ROOT"

# Project Sources publication
export AISTACK_LAPTOP_TARGET="big-brother@10.223.207.2"
export AISTACK_LAPTOP_DIR="Téléchargements/AIStack"
