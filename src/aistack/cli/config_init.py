"""
`python -m aistack.cli.config_init [DIRECTORY]` — fill a configuration
directory with every declaration AIStack ships (`ADR-0017` § 1).

The directory is `AISTACK_CONFIG_DIR` unless one is given. A file
already there is never overwritten: running it again after an upgrade
only adds the declarations a new version brought. The container runs it
at every start.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from aistack.config import CONFIG_DIR_ENV, config_dir, shipped_definitions


def init(directory: Path) -> tuple[list[str], list[str]]:
    """Copy each shipped declaration missing from `directory`; returns
    (copied, kept) file names."""

    directory.mkdir(parents=True, exist_ok=True)
    copied, kept = [], []
    for shipped in shipped_definitions():
        target = directory / shipped.name
        if target.exists():
            kept.append(shipped.name)
        else:
            shutil.copy2(shipped, target)
            copied.append(shipped.name)
    return copied, kept


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    directory = Path(arguments[0]) if arguments else config_dir()
    if directory is None:
        print(f"Refused: give a directory or set {CONFIG_DIR_ENV}.", file=sys.stderr)
        return 1

    copied, kept = init(directory)
    print(f"{directory}: {len(copied)} declaration(s) copied, {len(kept)} kept as they were.")
    for name in copied:
        print(f"  + {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
