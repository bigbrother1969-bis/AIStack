"""
Known accounts: profiles assigned to Pocket ID identifiers (`ADR-0034`).

Distinct from the sign-in journal (`aistack.authentication.sessions`):
an account can be pre-assigned a profile before it has ever signed in,
so this store exists independently of any session having occurred.
Keyed by email, case-folded — the identifier an admin names when
pre-assigning, and the one a signed-in session already carries.

The schema is versioned (`PRAGMA user_version`), the same discipline
as `SessionStore` (`ADR-0014` § 6): a database written by an earlier
version is rebuilt empty, which forgets every assignment.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1

ADMIN = "admin"
USER = "user"
# Denies access while leaving the Pocket ID account itself untouched
# (ADR-0034 § 1) — distinct from simply having no row: that falls
# through to the Pocket ID group instead.
REVOKED = "revoked"

_SCHEMA = """
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS profile_changes;
CREATE TABLE accounts (
    identifier TEXT PRIMARY KEY,
    profile TEXT NOT NULL,
    assigned_at REAL NOT NULL
);
CREATE TABLE profile_changes (
    at REAL NOT NULL,
    identifier TEXT NOT NULL,
    profile TEXT NOT NULL,
    by TEXT NOT NULL
);
"""


def _normalised(identifier: str) -> str:
    return identifier.strip().lower()


@dataclass(frozen=True)
class KnownAccount:
    identifier: str
    profile: str
    assigned_at: float


@dataclass(frozen=True)
class ProfileChange:
    at: float
    identifier: str
    profile: str
    by: str


class ProfileStore:
    """Who AIStack has an opinion about, beyond the Pocket ID group."""

    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self.path = path
        self.clock = clock
        self._lock = threading.Lock()
        self._ready = False

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            if not self._ready:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path)
            try:
                if not self._ready:
                    version = connection.execute("PRAGMA user_version").fetchone()[0]
                    if version != SCHEMA_VERSION:
                        connection.executescript(_SCHEMA)
                        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                    self._ready = True
                yield connection
                connection.commit()
            finally:
                connection.close()

    def assign(self, identifier: str, profile: str, by: str) -> None:
        """Pre-assign or change a profile — `ADMIN`, `USER`, or `REVOKED`
        to deny access while the Pocket ID account stays valid elsewhere.
        Always logged, even to repeat the same profile."""

        key = _normalised(identifier)
        now = self.clock()
        with self._db() as db:
            db.execute(
                "INSERT INTO accounts (identifier, profile, assigned_at) VALUES (?,?,?) "
                "ON CONFLICT(identifier) DO UPDATE SET profile = excluded.profile, "
                "assigned_at = excluded.assigned_at",
                (key, profile, now),
            )
            db.execute(
                "INSERT INTO profile_changes (at, identifier, profile, by) VALUES (?,?,?,?)",
                (now, key, profile, by),
            )

    def revoke(self, identifier: str, by: str) -> None:
        self.assign(identifier, REVOKED, by)

    def profile_for(self, identifier: str) -> str | None:
        """`ADMIN`, `USER`, `REVOKED`, or `None` — no individual
        assignment, fall through to the Pocket ID group."""

        with self._db() as db:
            row = db.execute(
                "SELECT profile FROM accounts WHERE identifier = ?", (_normalised(identifier),)
            ).fetchone()
        return row[0] if row else None

    def known(self) -> list[KnownAccount]:
        """Every account this store has an opinion about, most recently
        assigned first."""

        with self._db() as db:
            rows = db.execute(
                "SELECT identifier, profile, assigned_at FROM accounts ORDER BY assigned_at DESC"
            ).fetchall()
        return [KnownAccount(*row) for row in rows]

    def changes(self, limit: int = 200) -> list[ProfileChange]:
        """The profile-change log — who assigned what, when — most
        recent first."""

        with self._db() as db:
            rows = db.execute(
                "SELECT at, identifier, profile, by FROM profile_changes ORDER BY at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ProfileChange(*row) for row in rows]
