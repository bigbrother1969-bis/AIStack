"""
Server-side sessions, in SQLite (`ADR-0013` § 3, `ADR-0014` § 6).

The browser holds an opaque random identifier; the database holds only
its SHA-256, so a copy of the file opens no session. A session ends
after `idle` without a request or `absolute` in all; an expired row is
deleted when it is met. The same file keeps the pending sign-in
attempts (ten minutes) and the sign-in journal (thirty days).

The schema is versioned (`PRAGMA user_version`): a database written by
an earlier version is rebuilt empty, which signs everyone out once.
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

SCHEMA_VERSION = 2
PENDING_SECONDS = 10 * 60
JOURNAL_SECONDS = 30 * 86400
JOURNAL_LIMIT = 200

LOCAL = "local"
OIDC = "oidc"

PUBLIC_LISTENER = "public"
LAN_LISTENER = "lan"

# What the journal records.
SIGNED_IN = "signed_in"
SIGNED_OUT = "signed_out"
REFUSED = "refused"
LOCAL_FAILED = "local_failed"
LOCAL_LOCKED = "local_locked"
CLOSED_BY_ADMIN = "closed_by_admin"

_SCHEMA = """
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS pending;
DROP TABLE IF EXISTS journal;
CREATE TABLE sessions (
    id_hash TEXT PRIMARY KEY,
    public_id TEXT NOT NULL UNIQUE,
    subject TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    groups_json TEXT NOT NULL,
    method TEXT NOT NULL,
    listener TEXT NOT NULL,
    id_token TEXT NOT NULL,
    csrf TEXT NOT NULL,
    created REAL NOT NULL,
    last_seen REAL NOT NULL
);
CREATE TABLE pending (
    state TEXT PRIMARY KEY,
    nonce TEXT NOT NULL,
    verifier TEXT NOT NULL,
    next TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    listener TEXT NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE journal (
    at REAL NOT NULL,
    event TEXT NOT NULL,
    name TEXT NOT NULL,
    method TEXT NOT NULL,
    listener TEXT NOT NULL,
    detail TEXT NOT NULL
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
    public_id: str = ""
    listener: str = PUBLIC_LISTENER
    created: float = 0.0
    last_seen: float = 0.0


@dataclass(frozen=True)
class Pending:
    nonce: str
    verifier: str
    next: str
    redirect_uri: str = ""
    listener: str = PUBLIC_LISTENER


@dataclass(frozen=True)
class JournalEntry:
    at: float
    event: str
    name: str
    method: str
    listener: str
    detail: str


_SESSION_COLUMNS = (
    "subject, name, email, groups_json, method, id_token, csrf, public_id, listener, created, last_seen"
)


def _session(row: tuple) -> Session:  # type: ignore[type-arg]
    return Session(
        subject=row[0],
        name=row[1],
        email=row[2],
        groups=tuple(json.loads(row[3])),
        method=row[4],
        id_token=row[5],
        csrf=row[6],
        public_id=row[7],
        listener=row[8],
        created=row[9],
        last_seen=row[10],
    )


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
                    version = connection.execute("PRAGMA user_version").fetchone()[0]
                    if version != SCHEMA_VERSION:
                        connection.executescript(_SCHEMA)
                        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                    self._ready = True
                yield connection
                connection.commit()
            finally:
                connection.close()

    def _expired(self, created: float, last_seen: float, now: float) -> bool:
        return now - last_seen >= self.idle_seconds or now - created >= self.absolute_seconds

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
        listener: str = PUBLIC_LISTENER,
    ) -> str:
        """A new session; returns the identifier for the cookie."""

        identifier = secrets.token_urlsafe(32)
        now = self.clock()
        with self._db() as db:
            db.execute(
                f"INSERT INTO sessions (id_hash, {_SESSION_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    _digest(identifier),
                    subject,
                    name,
                    email,
                    json.dumps(list(groups)),
                    method,
                    id_token,
                    secrets.token_urlsafe(32),
                    secrets.token_urlsafe(12),
                    listener,
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
                f"SELECT {_SESSION_COLUMNS} FROM sessions WHERE id_hash = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            if self._expired(row[9], row[10], now):
                db.execute("DELETE FROM sessions WHERE id_hash = ?", (key,))
                return None
            db.execute("UPDATE sessions SET last_seen = ? WHERE id_hash = ?", (now, key))

        return _session(row[:10] + (now,))

    def close(self, identifier: str | None) -> None:
        if identifier:
            with self._db() as db:
                db.execute("DELETE FROM sessions WHERE id_hash = ?", (_digest(identifier),))

    def close_public(self, public_id: str) -> bool:
        """Close the session an administrator named by its public id."""

        with self._db() as db:
            return db.execute("DELETE FROM sessions WHERE public_id = ?", (public_id,)).rowcount > 0

    def live(self) -> list[Session]:
        """Every session still live, the most recently seen first;
        expired ones are deleted on the way."""

        now = self.clock()
        with self._db() as db:
            rows = db.execute(f"SELECT {_SESSION_COLUMNS} FROM sessions").fetchall()
            expired = [row[7] for row in rows if self._expired(row[9], row[10], now)]
            for public_id in expired:
                db.execute("DELETE FROM sessions WHERE public_id = ?", (public_id,))

        sessions = [_session(row) for row in rows if row[7] not in expired]
        return sorted(sessions, key=lambda session: session.last_seen, reverse=True)

    def count(self) -> int:
        with self._db() as db:
            return int(db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])

    def ends_at(self, session: Session) -> float:
        """When this session ends if nothing more is asked of it."""

        return min(session.last_seen + self.idle_seconds, session.created + self.absolute_seconds)

    # -- pending sign-ins ----------------------------------------------

    def remember(self, state: str, pending: Pending) -> None:
        now = self.clock()
        with self._db() as db:
            db.execute("DELETE FROM pending WHERE created <= ?", (now - PENDING_SECONDS,))
            db.execute(
                "INSERT INTO pending VALUES (?,?,?,?,?,?,?)",
                (
                    state,
                    pending.nonce,
                    pending.verifier,
                    pending.next,
                    pending.redirect_uri,
                    pending.listener,
                    now,
                ),
            )

    def take(self, state: str | None) -> Pending | None:
        """The attempt `state` names, once: it is deleted as it is read,
        and an expired one is refused."""

        if not state:
            return None

        now = self.clock()
        with self._db() as db:
            row = db.execute(
                "SELECT nonce, verifier, next, redirect_uri, listener, created FROM pending WHERE state = ?",
                (state,),
            ).fetchone()
            db.execute("DELETE FROM pending WHERE state = ?", (state,))

        if row is None or now - row[5] >= PENDING_SECONDS:
            return None

        return Pending(nonce=row[0], verifier=row[1], next=row[2], redirect_uri=row[3], listener=row[4])

    # -- the sign-in journal -------------------------------------------

    def record(self, event: str, *, name: str = "", method: str = "", listener: str = "", detail: str = "") -> None:
        now = self.clock()
        with self._db() as db:
            db.execute("DELETE FROM journal WHERE at <= ?", (now - JOURNAL_SECONDS,))
            db.execute(
                "INSERT INTO journal VALUES (?,?,?,?,?,?)",
                (now, event, name, method, listener, detail[:300]),
            )

    def journal(self, limit: int = JOURNAL_LIMIT) -> list[JournalEntry]:
        """The most recent events first, within the last thirty days."""

        since = self.clock() - JOURNAL_SECONDS
        with self._db() as db:
            rows = db.execute(
                "SELECT at, event, name, method, listener, detail FROM journal "
                "WHERE at > ? ORDER BY at DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        return [JournalEntry(*row) for row in rows]
