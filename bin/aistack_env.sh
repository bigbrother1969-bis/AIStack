#!/usr/bin/env bash

# ------------------------------------------------------------------
# AIStack execution environment.
#
# ADR-0001 designates this file as the single source of truth for
# the execution environment. This file is meant to be sourced:
#
#     source bin/aistack_env.sh
#
# It MUST NOT enable "set -e". A sourced script runs in the
# caller's shell, so `set -e` here terminates that shell the
# first time any command exits non-zero — a failing test run,
# for instance. `scripts/dev-env.sh` carried that warning for
# months while this file, the designated SPOT, did the opposite.
# The three launchers that source it declare their own
# `set -euo pipefail` before doing so, and keep it.
# ------------------------------------------------------------------

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

# AIStack has two source roots, and until 2026-08-21 this file
# declared one of them.
#
#   src/  holds the `aistack` package, per
#         `[tool.setuptools.packages.find] where = ["src"]`
#   .     holds `selection_ui`, `examples` and `tools`, which the
#         three launchers next to this file import
#
# Exporting only the repository root made `import aistack` fail,
# which is why ENG-TEST-0002 v1.0 asked every developer to type
# `PYTHONPATH=src` by hand and why `scripts/dev-env.sh` exported
# a third, different value. The environment had three
# declarations and the governed one covered half the tree.
export PYTHONPATH="$AISTACK_REPO_ROOT/src:$AISTACK_REPO_ROOT:${PYTHONPATH:-}"

cd "$AISTACK_REPO_ROOT" || return 1

# The gigabyte -> laptop delivery route was declared here as
# AISTACK_LAPTOP_TARGET / AISTACK_LAPTOP_DIR. Nothing read
# either variable, and both carried a private address and an
# account name into a published repository.
#
# The route is deployment configuration, not governed
# knowledge. It lives in config/context_bundle_transfer.yml,
# which is not versioned, and is overridable through
# AISTACK_TRANSFER_HOST / _USER / _PATH.
