"""
The quarantine register (`OPS-0012`): what is in quarantine, why, since
when, until when, and what has to be amended when it is deleted.

**Not a host declaration.** The register describes this code base, not
the host it runs on, so it sits next to this module rather than in a
`definitions/` directory: `config_init` never copies it into the
configuration directory, where it would stop following the code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

REGISTER = Path(__file__).resolve().parent / "register.yml"

# A file name that says nothing about which file it is: never searched
# for on its own when looking for references to a quarantined file.
GENERIC_NAMES = frozenset({"__init__.py", "README.md", ".gitkeep"})


@dataclass(frozen=True)
class QuarantineEntry:
    """One quarantined item: one or more files or directories, deleted together."""

    id: str
    paths: tuple[str, ...]
    reason: str
    since: date
    review_after: date
    amend: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("a quarantine entry has an identifier")
        if not self.paths:
            raise ValueError(f"{self.id}: a quarantine entry names at least one path")
        if any(path.startswith("/") or ".." in Path(path).parts for path in self.paths):
            raise ValueError(f"{self.id}: paths are relative to the repository root")
        if not self.reason.strip():
            raise ValueError(f"{self.id}: a quarantine entry says why")
        if self.review_after <= self.since:
            raise ValueError(f"{self.id}: the review comes after the entry into quarantine")

    def modules(self) -> tuple[str, ...]:
        """The Python modules the entry's paths hold, as imported."""

        return tuple(
            module
            for path in self.paths
            for module in _modules_of(path)
        )

    def holds(self, path: str) -> bool:
        """`path` (relative to the repository root) is one of the entry's files."""

        return any(path == own or (own.endswith("/") and path.startswith(own)) for own in self.paths)


def _modules_of(path: str) -> tuple[str, ...]:
    if path.endswith("/"):
        # A directory is the package of that name, when it can be one.
        parts = list(Path(path).parts)
        if parts and parts[0] == "src":
            parts = parts[1:]
        return (".".join(parts),) if parts and all(part.isidentifier() for part in parts) else ()
    if not path.endswith(".py"):
        return ()
    parts = list(Path(path).with_suffix("").parts)
    if parts[0] == "src":
        parts = parts[1:]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return (".".join(parts),) if parts else ()


def _date(value: object, entry: str, field: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError(f"{entry}: {field} is not a date ({value!r})") from error


def load_register(path: Path = REGISTER) -> tuple[QuarantineEntry, ...]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("entries") or []
    if not isinstance(raw, list):
        raise ValueError(f"{path}: `entries` is a list")
    entries = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"{path}: each entry is a mapping")
        identifier = str(item.get("id") or "")
        entries.append(
            QuarantineEntry(
                id=identifier,
                paths=tuple(str(value) for value in item.get("paths") or ()),
                reason=" ".join(str(item.get("reason") or "").split()),
                since=_date(item.get("since"), identifier, "since"),
                review_after=_date(item.get("review_after"), identifier, "review_after"),
                amend=tuple(str(value) for value in item.get("amend") or ()),
            )
        )
    identifiers = [entry.id for entry in entries]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError(f"{path}: an identifier is used twice")
    return tuple(entries)


def entry_of_module(entries: tuple[QuarantineEntry, ...], module: str) -> QuarantineEntry | None:
    for entry in entries:
        if any(module == own or module.startswith(own + ".") for own in entry.modules()):
            return entry
    return None


def entry_of_path(entries: tuple[QuarantineEntry, ...], path: str) -> QuarantineEntry | None:
    for entry in entries:
        if entry.holds(path):
            return entry
    return None
