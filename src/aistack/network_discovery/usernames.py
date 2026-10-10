"""
Adding and removing a candidate SSH username (`ADR-0012` § 4).

Every name is later tried, unattended, against every live host a LAN scan
finds (`aistack.cli.network_docker_discover`), so each change is one
explicit edit, never a bulk rewrite of the list.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from aistack.network_discovery.definition import NetworkDiscoveryDefinition


class UsernameChange(StrEnum):
    """What one add or remove did — the key of the message the screen shows."""

    ADDED = "added"
    ALREADY = "already"
    EMPTY = "empty"
    REMOVED = "removed"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class UsernameOutcome:
    """The definition after the change, whether it changed, and why."""

    definition: NetworkDiscoveryDefinition
    change: UsernameChange
    username: str

    @property
    def changed(self) -> bool:
        return self.change in (UsernameChange.ADDED, UsernameChange.REMOVED)


def add_username(definition: NetworkDiscoveryDefinition, submitted: str) -> UsernameOutcome:
    """
    Append one name to the ordered list. Blank or already present is a
    no-op, not an error, so a form submitted twice adds nothing.
    """

    username = submitted.strip()

    if not username:
        return UsernameOutcome(definition, UsernameChange.EMPTY, username)

    if username in definition.ssh_usernames:
        return UsernameOutcome(definition, UsernameChange.ALREADY, username)

    updated = replace(definition, ssh_usernames=(*definition.ssh_usernames, username))

    return UsernameOutcome(updated, UsernameChange.ADDED, username)


def remove_username(definition: NetworkDiscoveryDefinition, submitted: str) -> UsernameOutcome:
    """Remove one declared name, keeping the order of the others."""

    username = submitted.strip()

    if username not in definition.ssh_usernames:
        return UsernameOutcome(definition, UsernameChange.NOT_FOUND, username)

    updated = replace(
        definition,
        ssh_usernames=tuple(name for name in definition.ssh_usernames if name != username),
    )

    return UsernameOutcome(updated, UsernameChange.REMOVED, username)
