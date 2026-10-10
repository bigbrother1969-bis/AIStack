"""
Keeping a host's copies of the shipped declarations in step with new
versions (`ADR-0017`).

`config_init` copies each shipped declaration into the configuration
directory once and never overwrites it, so a later shipped change would
never reach an existing host. Therefore:

- A copy nobody edited follows the shipped file and is replaced at the next
  start. "Unedited" means it still matches the fingerprint recorded at copy
  time (`.shipped.json`), or exactly the shipped version last seen
  (`.shipped-seen.json`), which covers copies made by hand.
- A file the user edited or placed is never touched; when its shipped
  version changes, Settings shows the difference until the user marks it
  as seen. On the first start with this rule, the current shipped versions
  count as seen.
"""

from __future__ import annotations

import difflib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from aistack.config import PACKAGE_ROOT
from aistack.instance.first_start import SHIPPED_RECORD, fingerprint, read_record

SEEN_RECORD = ".shipped-seen.json"
# A difference longer than this is cut: the page says so.
MAX_DIFF_LINES = 200


@dataclass(frozen=True)
class Divergence:
    """A shipped declaration that changed since the user last saw it,
    and how it differs from the file in use."""

    name: str
    diff: tuple[str, ...]
    cut: bool
    # Where the shipped file is, under the package: `aistack/<area>/definitions/<name>`.
    shipped: str = ""


def _read(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(name): str(value) for name, value in data.items()} if isinstance(data, dict) else {}


def _write(path: Path, record: dict[str, str]) -> None:
    # Six services start together: write whole, never half a file.
    temporary = path.with_name(f"{path.name}.{os.getpid()}")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _copy(source: Path, target: Path) -> None:
    temporary = target.with_name(f".{target.name}.{os.getpid()}")
    temporary.write_bytes(source.read_bytes())
    temporary.replace(target)


def follow(directory: Path, shipped: list[Path]) -> list[str]:
    """
    Bring every untouched copy to its shipped version and record what the
    user has seen; return the names of the copies replaced. Run after
    `config_init` copied what was missing.
    """

    copies = read_record(directory)
    seen = _read(directory / SEEN_RECORD)
    replaced: list[str] = []
    for source in shipped:
        name = source.name
        target = directory / name
        if not target.is_file():
            continue
        current = fingerprint(source)
        in_use = fingerprint(target)
        recorded = copies.get(name)
        # Untouched: still what was copied, or (for a copy made by hand or
        # before `.shipped.json` existed) exactly the shipped version last
        # seen.
        untouched = (recorded is not None and in_use == recorded) or in_use == seen.get(name)
        if untouched and current != in_use:
            _copy(source, target)
            copies[name] = current
            replaced.append(name)
            in_use = current
        if in_use == current or name not in seen:
            seen[name] = current
    if replaced:
        _write(directory / SHIPPED_RECORD, copies)
    _write(directory / SEEN_RECORD, seen)
    return replaced


def divergences(directory: Path, shipped: list[Path]) -> list[Divergence]:
    """The shipped declarations that changed since the user last saw
    them, each with its difference from the file in use."""

    seen = _read(directory / SEEN_RECORD)
    found = []
    for source in shipped:
        name = source.name
        target = directory / name
        if not target.is_file() or name not in seen:
            continue
        current = fingerprint(source)
        if current == seen[name] or current == fingerprint(target):
            continue
        lines = list(
            difflib.unified_diff(
                target.read_text(encoding="utf-8", errors="replace").splitlines(),
                source.read_text(encoding="utf-8", errors="replace").splitlines(),
                fromfile=f"config/{name}",
                tofile=f"livré/{name}",
                lineterm="",
            )
        )
        found.append(
            Divergence(
                name,
                tuple(lines[:MAX_DIFF_LINES]),
                len(lines) > MAX_DIFF_LINES,
                shipped=_under_package(source),
            )
        )
    return found


def _under_package(source: Path) -> str:
    try:
        return source.resolve().relative_to(PACKAGE_ROOT.parent).as_posix()
    except ValueError:
        return source.name


def mark_seen(directory: Path, shipped: list[Path], name: str) -> bool:
    """Record that the user saw the shipped version of `name`; False
    when no shipped declaration has that name."""

    source = next((path for path in shipped if path.name == name), None)
    if source is None:
        return False
    seen = _read(directory / SEEN_RECORD)
    seen[name] = fingerprint(source)
    _write(directory / SEEN_RECORD, seen)
    return True
