#!/usr/bin/env bash
set -euo pipefail

# Repository root, derived from this script's own location.
# Overridable for a deployment that lives elsewhere.
#
# BASH_SOURCE, not $0: this file is sourced, so $0 is the
# caller's path, not this one.
#
# A machine path is not governed knowledge — same reason the
# Context Bundle transfer target is not versioned.
AISTACK_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AISTACK_REPO_ROOT="${AISTACK_REPO_ROOT:-$(cd "$AISTACK_ENV_DIR/.." && pwd)}"

export PYTHONPATH="$AISTACK_REPO_ROOT:${PYTHONPATH:-}"

cd "$AISTACK_REPO_ROOT"

# Project Sources publication
export AISTACK_LAPTOP_TARGET="big-brother@10.223.207.2"
export AISTACK_LAPTOP_DIR="Téléchargements/AIStack"
