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

# The gigabyte -> laptop delivery route was declared here as
# AISTACK_LAPTOP_TARGET / AISTACK_LAPTOP_DIR. Nothing read
# either variable, and both carried a private address and an
# account name into a published repository.
#
# The route is deployment configuration, not governed
# knowledge. It lives in config/context_bundle_transfer.yml,
# which is not versioned, and is overridable through
# AISTACK_TRANSFER_HOST / _USER / _PATH.
