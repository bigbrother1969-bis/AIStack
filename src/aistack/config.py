"""
Where AIStack's declarations are read from (`ADR-0017` § 1).

Every declaration ships inside the package, under
`src/aistack/<area>/definitions/<name>.yml`, with the values of the
reference host. When the environment names a configuration directory —
`AISTACK_CONFIG_DIR`, `/config` in the container — a file of the same
name there replaces the shipped one, file by file; a file it does not
hold keeps the shipped value. `python -m aistack.cli.config_init` copies
every shipped file into that directory, never overwriting one already
there, so a screen that saves a declaration (CPU priorities, SSH user
names) writes into the directory, not into the image.

Read when a module is imported: the directory is part of the process's
environment, set before it starts.
"""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_DIR_ENV = "AISTACK_CONFIG_DIR"
# The same directory as the host names it — `./config` beside
# `docker-compose.yml` — for what a page tells the owner to edit: the
# container's `/config` is not a path on the host (1.9).
CONFIG_HOST_DIR_ENV = "AISTACK_CONFIG_HOST_DIR"
# The reference host's own declarations (GIGABYTE's), read between the
# configuration directory and the shipped files (2.0.0-rc1, the owner
# 2026-10-10: a new installation "ne ramène aucune info de ma
# configuration actuelle : tout doit être découvert par AIStack"). The
# package ships neutral declarations; the reference values live in
# `tests/reference/definitions/`, which the test suite and a development
# checkout name here. Never set in the image.
REFERENCE_DIR_ENV = "AISTACK_REFERENCE_DIR"
PACKAGE_ROOT = Path(__file__).resolve().parent


def config_dir() -> Path | None:
    value = os.environ.get(CONFIG_DIR_ENV, "").strip()
    return Path(value) if value else None


def shown_config_dir() -> str | None:
    """The configuration directory as the owner finds it on the host:
    `AISTACK_CONFIG_HOST_DIR` when set, else the directory itself."""

    directory = config_dir()
    if directory is None:
        return None
    return os.environ.get(CONFIG_HOST_DIR_ENV, "").strip().rstrip("/") or str(directory)


def configured(shipped: Path) -> Path:
    """The declaration to read for `shipped`: the configuration
    directory's file of the same name when there is one, else the
    reference directory's (development and tests), else `shipped`."""

    for directory in (config_dir(), reference_dir()):
        if directory is not None:
            candidate = directory / shipped.name
            if candidate.is_file():
                return candidate
    return shipped


def reference_dir() -> Path | None:
    value = os.environ.get(REFERENCE_DIR_ENV, "").strip()
    return Path(value) if value else None


def shipped_definitions() -> list[Path]:
    """Every declaration the package ships, sorted by file name."""

    return sorted(PACKAGE_ROOT.glob("**/definitions/*.yml"), key=lambda path: path.name)
