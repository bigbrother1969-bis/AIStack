"""`aistack.network_discovery.usernames` — one explicit change at a time."""

from __future__ import annotations

from aistack.network_discovery.definition import NetworkDiscoveryDefinition
from aistack.network_discovery.usernames import UsernameChange, add_username, remove_username

DEFINITION = NetworkDiscoveryDefinition(
    cidr="192.168.1.0/24",
    ssh_key_path_env="AISTACK_SSH_KEY",
    ssh_usernames=("pi", "pi-hole"),
    ssh_timeout_seconds=3.0,
)


def test_a_new_name_is_appended_after_the_others():
    outcome = add_username(DEFINITION, "  admin ")

    assert outcome.change is UsernameChange.ADDED
    assert outcome.changed
    assert outcome.username == "admin"
    assert outcome.definition.ssh_usernames == ("pi", "pi-hole", "admin")


def test_adding_keeps_every_other_field():
    updated = add_username(DEFINITION, "admin").definition

    assert (updated.cidr, updated.ssh_key_path_env, updated.ssh_timeout_seconds) == (
        DEFINITION.cidr,
        DEFINITION.ssh_key_path_env,
        DEFINITION.ssh_timeout_seconds,
    )


def test_a_name_already_declared_is_not_added_twice():
    outcome = add_username(DEFINITION, "pi")

    assert outcome.change is UsernameChange.ALREADY
    assert not outcome.changed
    assert outcome.definition is DEFINITION


def test_a_blank_name_changes_nothing():
    outcome = add_username(DEFINITION, "   ")

    assert outcome.change is UsernameChange.EMPTY
    assert outcome.definition is DEFINITION


def test_removing_keeps_the_order_of_the_others():
    definition = add_username(DEFINITION, "admin").definition
    outcome = remove_username(definition, "pi-hole")

    assert outcome.change is UsernameChange.REMOVED
    assert outcome.definition.ssh_usernames == ("pi", "admin")


def test_removing_an_unknown_name_changes_nothing():
    outcome = remove_username(DEFINITION, "root")

    assert outcome.change is UsernameChange.NOT_FOUND
    assert outcome.definition is DEFINITION
