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

# The interpreter this heritage is verified on.
#
# ADR-0001 designates this file as the SPOT for the execution
# environment, and until 2026-08-23 that environment named its
# source roots and not its interpreter — while `pyproject.toml`
# declared a three-version range of which one was ever run.
#
# A warning, never an exit: this file is sourced, so a `return`
# here on a mismatch would drop the developer out of the very
# setup they asked for. It states the fact and lets them decide.
AISTACK_PYTHON_REQUIRED="3.13"

AISTACK_PYTHON_FOUND="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)"

if [ "$AISTACK_PYTHON_FOUND" != "$AISTACK_PYTHON_REQUIRED" ]; then
    echo "AIStack: python3 is $AISTACK_PYTHON_FOUND, this heritage is verified on $AISTACK_PYTHON_REQUIRED" >&2
    echo "AIStack: the suite will run, and it will not be running what the images ship" >&2
fi

export AISTACK_PYTHON_REQUIRED
