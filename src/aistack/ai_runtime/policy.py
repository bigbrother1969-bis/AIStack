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

_KEYS = ("callers", "internal_hosts")


@dataclass(frozen=True)
class AIPolicy:
    callers: dict[str, str] = field(default_factory=dict)
    internal_hosts: tuple[str, ...] = ()

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


def load_ai_policy(path: Path) -> AIPolicy:
    """
    The policy declared at `path`. A mistyped class, an unknown key or a
    caller that is not a name raises a `ValueError` naming it.
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(f"AI policy must contain a mapping: {path}")

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

    return AIPolicy(callers=callers, internal_hosts=tuple(hosts))


def current_policy() -> AIPolicy:
    """The declared policy, or the cautious one when it cannot be read (a question never waits for a file)."""

    try:
        return load_ai_policy(configured(SHIPPED))
    except (OSError, ValueError, yaml.YAMLError):
        return CAUTIOUS
