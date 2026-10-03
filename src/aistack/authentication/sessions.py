"""
Server-side sessions, in SQLite (`ADR-0013` § 3).

The browser holds an opaque random identifier; the database holds only
its SHA-256, so a copy of the file opens no session. A session ends
after `idle` without a request or `absolute` in all; an expired row is
deleted when it is met. The pending sign-in attempts (`state`, `nonce`,
PKCE verifier) live in the same file for ten minutes.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

PENDING_SECONDS = 10 * 60

LOCAL = "local"
OIDC = "oidc"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id_hash TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    groups_json TEXT NOT NULL,
    method TEXT NOT NULL,
    id_token TEXT NOT NULL,
    csrf TEXT NOT NULL,
    created REAL NOT NULL,
    last_seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS pending (
    state TEXT PRIMARY KEY,
    nonce TEXT NOT NULL,
    verifier TEXT NOT NULL,
    next TEXT NOT NULL,
    created REAL NOT NULL
);
"""


def _digest(identifier: str) -> str:
    return hashlib.sha256(identifier.encode("ascii", "replace")).hexdigest()


@dataclass(frozen=True)
class Session:
    subject: str
    name: str
    email: str
    groups: tuple[str, ...]
    method: str
    id_token: str
    csrf: str


@dataclass(frozen=True)
class Pending:
    nonce: str
    verifier: str
    next: str


class SessionStore:
    def __init__(
        self,
        path: Path,
        idle_seconds: float,
        absolute_seconds: float,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = path
        self.idle_seconds = idle_seconds
        self.absolute_seconds = absolute_seconds
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
                    connection.executescript(_SCHEMA)
                    self._ready = True
                yield connection
                connection.commit()
            finally:
                connection.close()

    # -- sessions ------------------------------------------------------

    def open(
        self,
        *,
        subject: str,
        name: str,
        email: str = "",
        groups: tuple[str, ...] = (),
        method: str,
        id_token: str = "",
    ) -> str:
        """A new session; returns the identifier for the cookie."""

        identifier = secrets.token_urlsafe(32)
        now = self.clock()
        with self._db() as db:
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    _digest(identifier),
                    subject,
                    name,
                    email,
                    json.dumps(list(groups)),
                    method,
                    id_token,
                    secrets.token_urlsafe(32),
                    now,
                    now,
                ),
            )
        return identifier

    def get(self, identifier: str | None) -> Session | None:
        """The live session for this identifier, its idle clock reset;
        `None` — and the row deleted — when it has expired."""

        if not identifier:
            return None

        key = _digest(identifier)
        now = self.clock()
        with self._db() as db:
            row = db.execute(
                "SELECT subject, name, email, groups_json, method, id_token, csrf, created, last_seen "
                "FROM sessions WHERE id_hash = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None

            created, last_seen = row[7], row[8]
            if now - last_seen >= self.idle_seconds or now - created >= self.absolute_seconds:
                db.execute("DELETE FROM sessions WHERE id_hash = ?", (key,))
                return None

            db.execute("UPDATE sessions SET last_seen = ? WHERE id_hash = ?", (now, key))

        return Session(
            subject=row[0],
            name=row[1],
            email=row[2],
            groups=tuple(json.loads(row[3])),
            method=row[4],
            id_token=row[5],
            csrf=row[6],
        )

    def close(self, identifier: str | None) -> None:
        if identifier:
            with self._db() as db:
                db.execute("DELETE FROM sessions WHERE id_hash = ?", (_digest(identifier),))

    def count(self) -> int:
        with self._db() as db:
            return int(db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])

    # -- pending sign-ins ----------------------------------------------

    def remember(self, state: str, pending: Pending) -> None:
        now = self.clock()
        with self._db() as db:
            db.execute("DELETE FROM pending WHERE created <= ?", (now - PENDING_SECONDS,))
            db.execute(
                "INSERT INTO pending VALUES (?,?,?,?,?)",
                (state, pending.nonce, pending.verifier, pending.next, now),
            )

    def take(self, state: str | None) -> Pending | None:
        """The attempt `state` names, once: it is deleted as it is read,
        and an expired one is refused."""

        if not state:
            return None

        now = self.clock()
        with self._db() as db:
            row = db.execute(
                "SELECT nonce, verifier, next, created FROM pending WHERE state = ?", (state,)
            ).fetchone()
            db.execute("DELETE FROM pending WHERE state = ?", (state,))

        if row is None or now - row[3] >= PENDING_SECONDS:
            return None

        return Pending(nonce=row[0], verifier=row[1], next=row[2])
