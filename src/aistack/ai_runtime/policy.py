"""
`ai_policy.yml` (`ADR-0029` § 2 to § 4): which use of a model may send what it
asks outside the owner's machines, and which engines are outside them.

Hand-written and read-only. A caller the file does not name is `internal_only`:
in doubt, nothing leaves. Nothing in this module routes a question; it only
says what the declaration allows, so the journal can show what a routing by
policy would have changed before any routing exists (`ADR-0029` M2).
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from aistack.config import configured

SHIPPED = Path(__file__).resolve().parent / "definitions" / "ai_policy.yml"

INTERNAL_ONLY = "internal_only"
EXTERNAL_ALLOWED = "external_allowed"
CLASSES = (INTERNAL_ONLY, EXTERNAL_ALLOWED)

INTERNAL = "internal"
EXTERNAL = "external"

_KEYS = ("callers", "internal_hosts", "kinds", "preferences")


@dataclass(frozen=True)
class Preference:
    """
    One line of the table of `ADR-0029` § 10: an engine, and why the owner puts it there.

    `engine` is `gemini`, `openai` (ChatGPT), `anthropic` (Claude), `local` (the local engines in
    the order declared), or the label or model of one local engine ("Olala", "qwen2.5:7b").
    """

    engine: str
    why: str


@dataclass(frozen=True)
class AIPolicy:
    callers: dict[str, str] = field(default_factory=dict)
    internal_hosts: tuple[str, ...] = ()
    # Operation (or `caller.operation`) to the kind of request it is, and kind to the engines it prefers, best first.
    kinds: dict[str, str] = field(default_factory=dict)
    preferences: dict[str, tuple[Preference, ...]] = field(default_factory=dict)
    # The blocks the declaration did not hold and the shipped file supplied (`ADR-0017` § 1): shown, never written.
    completed: tuple[str, ...] = ()

    def kind_of(self, caller: str, operation: str) -> str:
        """The kind of request a call is: declared for `caller.operation`, else for the operation; empty when not declared."""

        return self.kinds.get(f"{caller}.{operation}") or self.kinds.get(operation) or ""

    def preferred(self, kind: str) -> tuple[Preference, ...]:
        """The engines a kind prefers, best first; empty when the kind has no list."""

        return self.preferences.get(kind, ())

    def class_of(self, caller: str) -> str:
        """The class of a use of a model; a caller the file does not name is internal."""

        return self.callers.get(caller, INTERNAL_ONLY)

    def kind_of_host(self, host: str) -> str:
        """`internal` for an engine on the loopback, on a private (LAN) address or in `internal_hosts`; else `external`."""

        if host in self.internal_hosts:
            return INTERNAL

        try:
            address = ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            return EXTERNAL

        return INTERNAL if address.is_loopback or address.is_private or address.is_link_local else EXTERNAL

    def allows_external(self, caller: str) -> bool:
        return self.class_of(caller) == EXTERNAL_ALLOWED


# What is read when no declaration can be: every use internal.
CAUTIOUS = AIPolicy()


# The blocks a copy of the file may lack and the shipped file then supplies. Never `callers` or
# `internal_hosts`: they decide what may leave, and a caller not named stays internal.
_COMPLETED = ("kinds", "preferences")


def _read(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(f"AI policy must contain a mapping: {path}")

    return data


# Entries that arrived after the first copies of ai_policy.yml were made, by block.
_ADDED = {"kinds": ("ask",), "preferences": ("question",)}


def load_ai_policy(path: Path, completing: Path | None = None) -> AIPolicy:
    """
    The policy declared at `path`. A mistyped class, an unknown key or a
    caller that is not a name raises a `ValueError` naming it.

    With `completing`, the file shipped with the package: `kinds` and `preferences`, when `path` does
    not name them at all, are read from it (a copy made before they existed keeps working) and
    listed in `completed`. A block the copy names, even empty, is the owner's and is never replaced.
    """

    data = _read(path)
    completed: list[str] = []

    if completing is not None and completing.resolve() != path.resolve():
        shipped = _read(completing)

        for block in _COMPLETED:
            if block not in data and block in shipped:
                data[block] = shipped[block]
                completed.append(block)

        # An entry added to a block after copies were made (the question page, ADR-0029 § 12): read from the
        # shipped file when the copy's block lacks it; the entries the owner has are never touched.
        for block, entries in _ADDED.items():
            mine, theirs = data.get(block), shipped.get(block)
            if isinstance(mine, dict) and mine and isinstance(theirs, dict):
                for entry in entries:
                    if entry not in mine and entry in theirs:
                        data[block] = mine = {**mine, entry: theirs[entry]}
                        completed.append(f"{block} ({entry})")

    unknown = [key for key in data if key not in _KEYS]
    if unknown:
        raise ValueError(f"AI policy {path}: unknown key {unknown[0]!r} (one of {', '.join(_KEYS)})")

    raw = data.get("callers")
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"AI policy {path}: callers must be a mapping of a caller to its class")

    callers: dict[str, str] = {}
    for caller, declared in raw.items():
        if not isinstance(caller, str) or not caller.strip():
            raise ValueError(f"AI policy {path}: a caller is a name, not {caller!r}")
        if declared not in CLASSES:
            raise ValueError(f"AI policy {path}: caller {caller!r} has an unknown class {declared!r} (one of {', '.join(CLASSES)})")
        callers[caller] = declared

    hosts = data.get("internal_hosts")
    if hosts is None:
        hosts = []
    if not isinstance(hosts, list) or not all(isinstance(item, str) and item.strip() for item in hosts):
        raise ValueError(f"AI policy {path}: internal_hosts must be a list of host names")

    return AIPolicy(
        callers=callers,
        internal_hosts=tuple(hosts),
        kinds=_kinds(data.get("kinds"), path),
        preferences=_preferences(data.get("preferences"), path),
        completed=tuple(completed),
    )


def _kinds(raw: object, path: Path) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"AI policy {path}: kinds must be a mapping of an operation (or caller.operation) to a kind")
    kinds: dict[str, str] = {}
    for use, kind in raw.items():
        if not isinstance(use, str) or not use.strip() or not isinstance(kind, str) or not kind.strip():
            raise ValueError(f"AI policy {path}: kinds: {use!r}: {kind!r} must be a name given to a name")
        kinds[use] = kind
    return kinds


def _preferences(raw: object, path: Path) -> dict[str, tuple[Preference, ...]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"AI policy {path}: preferences must be a mapping of a kind to a list of engines")
    table: dict[str, tuple[Preference, ...]] = {}
    for kind, items in raw.items():
        if not isinstance(kind, str) or not kind.strip() or not isinstance(items, list):
            raise ValueError(f"AI policy {path}: preferences: {kind!r} must be a list of engines, best first")
        lines: list[Preference] = []
        for item in items:
            engine = item.get("engine") if isinstance(item, dict) else None
            why = item.get("why") if isinstance(item, dict) else None
            if not isinstance(engine, str) or not engine.strip() or not isinstance(why, str) or not why.strip():
                raise ValueError(f"AI policy {path}: preferences: {kind}: each line names an engine and says why")
            lines.append(Preference(engine.strip(), why.strip()))
        table[kind] = tuple(lines)
    return table


def current_policy() -> AIPolicy:
    """The declared policy, or the cautious one when it cannot be read (a question never waits for a file)."""

    try:
        return load_ai_policy(configured(SHIPPED), completing=SHIPPED)
    except (OSError, ValueError, yaml.YAMLError):
        return CAUTIOUS
