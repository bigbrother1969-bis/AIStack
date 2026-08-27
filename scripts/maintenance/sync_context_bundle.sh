#!/bin/bash

set -euo pipefail

# Repository root, derived from this script's own location.
# Overridable for a deployment that lives elsewhere.
#
# A machine path is not governed knowledge — same reason the
# Context Bundle transfer target was taken out of the repo.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

ROOT="${AISTACK_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

LOG_DIR="$ROOT/logs"

LOG_FILE="$LOG_DIR/context_bundle_sync.log"


mkdir -p "$LOG_DIR"


echo "===== Context Bundle Sync $(date -Iseconds) =====" >> "$LOG_FILE"


cd "$ROOT"


# The declared execution environment, and a refusal if it is not
# there.
#
# Until 2026-08-27 this script called `python3` directly, so the
# projection it regenerates four times a day was produced by
# whichever interpreter the host distribution installs.
# ENG-TEST-0002 is C3 and asks for reproducibility across
# environments, and GOV-0002/OS-019 measured what that axis costs:
# the same contract inventory gave 20 orphan contracts on one
# interpreter and 22 on another, at the same commit. A projection
# is not a place to find that out.
#
# `scripts/dev-env.sh` sources the declaration and puts the
# project virtual environment ahead of the system interpreter. It
# does not guarantee one is there — so the check below does, and
# **this script refuses rather than produces a doubtful
# projection**. The message goes to stderr, which cron mails,
# rather than to the log file nobody opens (GOV-0002/OS-031).
source "$ROOT/scripts/dev-env.sh" >> "$LOG_FILE" 2>&1

FOUND="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

if [ "$FOUND" != "${AISTACK_PYTHON_REQUIRED:-}" ]; then
    echo "AIStack: refusing to regenerate the projection." >&2
    echo "  python3 is $FOUND, this heritage is verified on ${AISTACK_PYTHON_REQUIRED:-unknown}" >&2
    echo "  the declared environment was sourced and did not provide it" >&2
    echo "===== Refused: python3 is $FOUND =====" >> "$LOG_FILE"
    exit 1
fi


python3 scripts/export_project_sources.py \
    >> "$LOG_FILE" 2>&1


echo "===== Completed $(date -Iseconds) =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
