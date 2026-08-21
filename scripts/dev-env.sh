#!/usr/bin/env bash

# ------------------------------------------------------------------
# AIStack Development Environment
#
# This script is intended to be sourced:
#
#     source scripts/dev-env.sh
#
# It adds the developer conveniences — the project venv on PATH,
# and a report of what is actually being used — on top of the
# execution environment.
#
# It does NOT declare that environment. ADR-0001 names
# `bin/aistack_env.sh` as its single source of truth, and until
# 2026-08-21 this file exported a different PYTHONPATH than the
# SPOT it was supposed to follow. Two files declaring the same
# thing differently is how a developer ends up with an
# environment nobody can describe.
#
# It MUST NOT enable "set -e", because that would terminate the
# developer's shell whenever a command (such as pytest) exits
# non-zero.
# ------------------------------------------------------------------

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source "${PROJECT_ROOT}/bin/aistack_env.sh" || return 1

export PATH="${PROJECT_ROOT}/.venv/bin:${PATH}"

echo "AIStack development environment activated."
echo "Python     : $(command -v python)"
echo "Pytest     : $(command -v pytest)"
echo "PYTHONPATH : ${PYTHONPATH}"
