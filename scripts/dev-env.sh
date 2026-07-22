#!/usr/bin/env bash

# ------------------------------------------------------------------
# AIStack Development Environment
#
# This script is intended to be sourced:
#
#     source scripts/dev-env.sh
#
# It configures the interactive shell for development.
# It MUST NOT enable "set -e", because that would terminate the
# developer's shell whenever a command (such as pytest) exits non-zero.
# ------------------------------------------------------------------

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PYTHONPATH="${PROJECT_ROOT}/src"
export PATH="${PROJECT_ROOT}/.venv/bin:${PATH}"

cd "${PROJECT_ROOT}" || return 1

echo "AIStack development environment activated."
echo "Python : $(command -v python)"
echo "Pytest : $(command -v pytest)"
