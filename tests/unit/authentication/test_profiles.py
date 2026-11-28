"""`aistack.authentication.profiles` (`ADR-0034`)."""

from __future__ import annotations

from pathlib import Path

from aistack.authentication.profiles import ADMIN, REVOKED, USER, ProfileStore


def store(tmp_path: Path, now: list[float]) -> ProfileStore:
    return ProfileStore(tmp_path / "web" / "profiles.sqlite3", clock=lambda: now[0])


def test_an_unknown_identifier_has_no_profile(tmp_path: Path):
    profiles = store(tmp_path, [0.0])

    assert profiles.profile_for("nobody@example.com") is None
    assert profiles.known() == []


def test_assigning_pre_assigns_before_any_sign_in(tmp_path: Path):
    profiles = store(tmp_path, [1000.0])

    profiles.assign("Ada@Example.com", ADMIN, by="owner")

    # Case-folded: the identifier a session carries need not match case.
    assert profiles.profile_for("ada@example.com") == ADMIN
    known = profiles.known()
    assert len(known) == 1 and known[0].identifier == "ada@example.com" and known[0].profile == ADMIN


def test_reassigning_replaces_the_profile_not_adds_a_row(tmp_path: Path):
    profiles = store(tmp_path, [1000.0])

    profiles.assign("ada@example.com", USER, by="owner")
    profiles.assign("ada@example.com", ADMIN, by="owner")

    assert profiles.profile_for("ada@example.com") == ADMIN
    assert len(profiles.known()) == 1


def test_revoking_denies_access_without_a_separate_state(tmp_path: Path):
    profiles = store(tmp_path, [1000.0])
    profiles.assign("ada@example.com", ADMIN, by="owner")

    profiles.revoke("ada@example.com", by="owner")

    assert profiles.profile_for("ada@example.com") == REVOKED


def test_every_assignment_is_logged_most_recent_first(tmp_path: Path):
    now = [1000.0]
    profiles = store(tmp_path, now)

    profiles.assign("ada@example.com", USER, by="owner")
    now[0] = 2000.0
    profiles.assign("ada@example.com", ADMIN, by="owner")
    now[0] = 3000.0
    profiles.revoke("ada@example.com", by="owner")

    changes = profiles.changes()
    assert [change.profile for change in changes] == [REVOKED, ADMIN, USER]
    assert all(change.identifier == "ada@example.com" and change.by == "owner" for change in changes)


def test_a_database_from_an_earlier_schema_is_rebuilt_empty(tmp_path: Path):
    import sqlite3

    path = tmp_path / "web" / "profiles.sqlite3"
    path.parent.mkdir(parents=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE accounts (identifier TEXT PRIMARY KEY)")
    connection.execute("INSERT INTO accounts VALUES ('ghost@example.com')")
    connection.commit()
    connection.close()

    profiles = store(tmp_path, [0.0])

    assert profiles.profile_for("ghost@example.com") is None
    assert profiles.known() == []
