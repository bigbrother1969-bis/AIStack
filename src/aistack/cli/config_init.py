"""
`python -m aistack.cli.config_init [DIRECTORY]` — fill a configuration directory with every shipped declaration (ADR-0017 § 1).

The directory is `AISTACK_CONFIG_DIR` unless one is given. A file the
owner edited or added is never overwritten; an unedited copy follows the
shipped version when it changes (`aistack.instance.declarations`). The
container runs this at every start.

Each copy's fingerprint is kept in `.shipped.json`, so the web
application can tell a declaration still holding the reference host's
values from one the owner wrote (ADR-0017 § 4).
"""

from __future__ import annotations

import fcntl
import shutil
import sys
from pathlib import Path

from aistack.config import CONFIG_DIR_ENV, config_dir, shipped_definitions
from aistack.instance.declarations import SEEN_RECORD, follow
from aistack.instance.first_start import SHIPPED_RECORD, remember_copies

# Which shipped declarations a directory's records describe. Generation 2
# ships neutral declarations; a directory filled before holds the
# reference host's values, which become the owner's files and are never
# followed to the neutral ones.
GENERATION_FILE = ".shipped-generation"
GENERATION = "2"
LOCK_FILE = ".config_init.lock"


def adopt_older_copies(directory: Path) -> bool:
    """Make the declarations of a pre-generation-2 directory the owner's own; True when there were any."""

    marker = directory / GENERATION_FILE
    try:
        if marker.read_text(encoding="utf-8").strip() == GENERATION:
            return False
    except OSError:
        pass
    older = any(directory.glob("*.yml"))
    if older:
        (directory / SHIPPED_RECORD).unlink(missing_ok=True)
        (directory / SEEN_RECORD).unlink(missing_ok=True)
    marker.write_text(GENERATION + "\n", encoding="utf-8")
    return older


def init(directory: Path) -> tuple[list[str], list[str], list[str]]:
    """Copy missing shipped declarations and update untouched copies; return (copied, kept, updated) names."""

    directory.mkdir(parents=True, exist_ok=True)
    # Seven containers start together and each runs this: one at a time.
    with (directory / LOCK_FILE).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return _init(directory)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _init(directory: Path) -> tuple[list[str], list[str], list[str]]:
    adopt_older_copies(directory)
    copied, kept = [], []
    shipped_files = shipped_definitions()
    for shipped in shipped_files:
        target = directory / shipped.name
        if target.exists():
            kept.append(shipped.name)
        else:
            shutil.copy2(shipped, target)
            copied.append(shipped.name)
    remember_copies(directory, copied)
    updated = follow(directory, shipped_files)
    return copied, kept, updated


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    directory = Path(arguments[0]) if arguments else config_dir()
    if directory is None:
        print(f"Refused: give a directory or set {CONFIG_DIR_ENV}.", file=sys.stderr)
        return 1

    copied, kept, updated = init(directory)
    print(
        f"{directory}: {len(copied)} declaration(s) copied, {len(updated)} untouched "
        f"cop(y/ies) brought to the shipped version, {len(kept) - len(updated)} kept as they were."
    )
    for name in copied:
        print(f"  + {name}")
    for name in updated:
        print(f"  ~ {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
