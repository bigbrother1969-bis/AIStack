#!/usr/bin/env bash
#
# AIStack's own backup (OPS-0010, 1.9 — decided by the owner 2026-10-05:
# a script and a systemd timer on the host, hot, every night at 03:00,
# 30 days kept, the secrets included in an archive only its owner reads).
#
# One archive per run, `aistack-<UTC stamp>.tar.gz`, in
# AISTACK_BACKUP_DIR (default /media/BACKUP/AIStack), holding:
#
#   data/     AIStack's data — AISTACK_DATA_DIR when `.env` names it
#             (docker compose), else reports/generated — except the
#             Time Machine graph, a projection `timemachine_rebuild`
#             rebuilds from the files (ADR-0011 § 1), and the live
#             session database, taken separately:
#   sessions.sqlite3   a consistent copy of data/web/sessions.sqlite3,
#             made by SQLite's own backup API while the web keeps running;
#   config/   the declarations (./config);
#   env/      .env, .env.web, .env.resource-priority — secrets: the
#             archive is created mode 600 in a directory mode 700;
#   MANIFEST  when, where, which commit and which image version.
#
# Hot: the histories are append-only files, so a file written during
# the run is either in the archive or in the next one. Nothing is
# stopped. Run from anywhere, as the account AIStack runs as.
#
# Restore: scripts/restore_aistack.sh (OPS-0010 § AIStack's own backup).

set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${AISTACK_BACKUP_DIR:-/media/BACKUP/AIStack}"
KEEP_DAYS="${AISTACK_BACKUP_KEEP_DAYS:-30}"

data_dir() {
    local value=""
    if [ -f "$ROOT/.env" ]; then
        value="$(sed -n 's/^AISTACK_DATA_DIR=//p' "$ROOT/.env" | tail -1)"
    fi
    case "$value" in
        "") echo "$ROOT/reports/generated" ;;
        /*) echo "$value" ;;
        *) echo "$ROOT/${value#./}" ;;
    esac
}

DATA="$(data_dir)"
if [ ! -d "$DATA" ]; then
    echo "Refused: no data directory at $DATA" >&2
    exit 1
fi
mkdir -p "$DEST"
chmod 700 "$DEST"

stamp="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# The session database, consistent while the web application writes it.
sessions="$DATA/web/sessions.sqlite3"
if [ -f "$sessions" ]; then
    python3 - "$sessions" "$work/sessions.sqlite3" <<'PY'
import sqlite3, sys
source = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
target = sqlite3.connect(sys.argv[2])
source.backup(target)
target.close()
source.close()
PY
fi

mkdir -p "$work/env"
for name in .env .env.web .env.resource-priority; do
    [ -f "$ROOT/$name" ] && cp -p "$ROOT/$name" "$work/env/$name"
done

{
    echo "created: $stamp"
    echo "host: $(hostname)"
    echo "commit: $(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "image_version: $(sed -n 's/^AISTACK_VERSION=//p' "$ROOT/.env" 2>/dev/null | tail -1)"
    echo "data: $DATA"
} > "$work/MANIFEST"

members=(MANIFEST env)
[ -f "$work/sessions.sqlite3" ] && members+=(sessions.sqlite3)

archive="$DEST/aistack-$stamp.tar.gz"
partial="$archive.partial"
started=$SECONDS

# The data directory's members start with "./"; renamed to data/ in the
# archive. Exit status 1 is GNU tar's "a file changed while read" — a
# history being appended to, kept for the next run.
set +e
tar -czf "$partial" \
    --warning=no-file-changed \
    --transform='flags=r;s,^\./,data/,' \
    --exclude='./timemachine/graph' \
    --exclude='./web/sessions.sqlite3*' \
    -C "$DATA" . \
    -C "$ROOT" config \
    -C "$work" "${members[@]}"
status=$?
set -e
if [ "$status" -gt 1 ]; then
    rm -f "$partial"
    echo "Failed: tar exited with $status" >&2
    exit "$status"
fi

tar -tzf "$partial" > /dev/null
chmod 600 "$partial"
mv "$partial" "$archive"

find "$DEST" -maxdepth 1 -name 'aistack-*.tar.gz' -mtime +"$KEEP_DAYS" -delete
find "$DEST" -maxdepth 1 -name 'aistack-*.tar.gz.partial' -mtime +1 -delete

echo "AIStack backed up: $archive ($(du -h "$archive" | cut -f1), $((SECONDS - started)) s)"
