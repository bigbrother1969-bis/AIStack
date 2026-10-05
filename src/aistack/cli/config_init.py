"""
`python -m aistack.cli.config_init [DIRECTORY]` — fill a configuration
directory with every declaration AIStack ships (`ADR-0017` § 1).

The directory is `AISTACK_CONFIG_DIR` unless one is given. A file the
owner edited, or put there himself, is never overwritten; a copy nobody
edited follows the shipped version when a new version changes it
(`aistack.instance.declarations`, decided by the owner 2026-10-05).
The container runs it at every start.

Each copy's fingerprint is kept in the directory's `.shipped.json`, so
the web application can tell a declaration still holding the reference
host's values from one the owner wrote (`ADR-0017` § 4).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from aistack.config import CONFIG_DIR_ENV, config_dir, shipped_definitions
from aistack.instance.declarations import follow
from aistack.instance.first_start import remember_copies


def init(directory: Path) -> tuple[list[str], list[str], list[str]]:
    """Copy each shipped declaration missing from `directory`, and bring
    each untouched copy to its shipped version; returns (copied, kept,
    updated) file names."""

    directory.mkdir(parents=True, exist_ok=True)
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
