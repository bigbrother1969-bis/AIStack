#!/usr/bin/env bash
#
# Restore an AIStack backup (scripts/backup_aistack.sh) into a NEW
# directory, and check it — never over the live installation
# (OPS-0010 § AIStack's own backup, 1.9).
#
#   scripts/restore_aistack.sh /media/BACKUP/AIStack/aistack-<stamp>.tar.gz /tmp/aistack-restore
#
# Leaves <target>/data (with web/sessions.sqlite3 back in place),
# <target>/config and <target>/env, checks the session database
# (PRAGMA integrity_check) and every Explication file (valid JSON), and
# prints what was restored and the command that rebuilds the Time
# Machine graph from the restored files in a throwaway container — the
# proof that the data is usable, not only present.
#
# Putting a restored copy in production is the owner's act, by hand.

set -euo pipefail
umask 077

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 ARCHIVE TARGET_DIRECTORY" >&2
    exit 2
fi
archive="$1"
target="$2"

if [ ! -f "$archive" ]; then
    echo "Refused: no archive at $archive" >&2
    exit 1
fi
if [ -e "$target" ] && [ -n "$(ls -A "$target" 2>/dev/null)" ]; then
    echo "Refused: $target exists and is not empty — restore into a new directory" >&2
    exit 1
fi

started=$SECONDS
mkdir -p "$target"
tar -xzf "$archive" -C "$target"

if [ -f "$target/sessions.sqlite3" ]; then
    mkdir -p "$target/data/web"
    mv "$target/sessions.sqlite3" "$target/data/web/sessions.sqlite3"
fi

python3 - "$target" <<'PY'
import json, sqlite3, sys
from pathlib import Path

target = Path(sys.argv[1])
data = target / "data"
problems = []

sessions = data / "web" / "sessions.sqlite3"
if sessions.is_file():
    result = sqlite3.connect(sessions).execute("PRAGMA integrity_check").fetchone()[0]
    print(f"  sessions database: {result}")
    if result != "ok":
        problems.append("sessions database")
else:
    print("  sessions database: none in this archive")

explications = list((data / "explications").rglob("*.json")) if (data / "explications").is_dir() else []
broken = 0
for path in explications:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        broken += 1
print(f"  explications: {len(explications)} file(s), {broken} unreadable")
if broken:
    problems.append("explications")

history = data / "history"
streams = sorted(child.name for child in history.iterdir() if child.is_dir()) if history.is_dir() else []
files = sum(1 for _ in history.rglob("*") if _.is_file()) if history.is_dir() else 0
print(f"  history: {len(streams)} stream(s), {files} file(s)")

declarations = sorted(path.name for path in (target / "config").glob("*.yml")) if (target / "config").is_dir() else []
print(f"  declarations: {len(declarations)}")
secrets = sorted(path.name for path in (target / "env").iterdir()) if (target / "env").is_dir() else []
print(f"  environment files: {', '.join(secrets) or 'none'}")

manifest = target / "MANIFEST"
if manifest.is_file():
    print("  " + manifest.read_text(encoding="utf-8").strip().replace("\n", "\n  "))

sys.exit(1 if problems else 0)
PY

echo "Restored into $target in $((SECONDS - started)) s."
echo "Rebuild the Time Machine graph from the restored files, in a throwaway container:"
echo "  time docker run --rm --network none -u \"\$(id -u):\$(id -g)\" \\"
echo "    -v \"$target/data:/app/reports/generated\" -v \"$target/config:/config\" \\"
echo "    bigbrother1969/aistack-core:\${AISTACK_VERSION:-dev} python -m aistack.cli.timemachine_rebuild"
