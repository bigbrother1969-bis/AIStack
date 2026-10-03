"""
The local fallback administrator (`ADR-0013` § 5): one password, kept
only as an scrypt hash, tried on the LAN port only, and refused for a
while after five failures.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

SCHEME = "scrypt"
N, R, P = 2**15, 8, 1
SALT_BYTES = 16
KEY_BYTES = 32
# scrypt needs 128 * n * r bytes; the default 32 MiB cap is exactly
# that, so give it headroom rather than fail on a cap at the boundary.
MAXMEM = 64 * 1024 * 1024

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str, salt: bytes | None = None) -> str:
    """`scrypt$n$r$p$salt$key` — what `.env.web` stores."""

    if not password:
        raise ValueError("an empty password cannot be stored")

    salt = salt if salt is not None else secrets.token_bytes(SALT_BYTES)
    key = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=N, r=R, p=P, maxmem=MAXMEM, dklen=KEY_BYTES
    )
    return f"{SCHEME}${N}${R}${P}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, stored: str) -> bool:
    """Whether `password` matches `stored`; a malformed hash matches nothing."""

    try:
        scheme, n, r, p, salt, key = stored.split("$")
        if scheme != SCHEME:
            return False
        expected = _unb64(key)
        computed = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_unb64(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            maxmem=MAXMEM,
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(computed, expected)


@dataclass
class FailureWindow:
    """Refuses every attempt once `MAX_FAILURES` failed within
    `WINDOW_SECONDS`, until the oldest of them leaves the window."""

    clock: Callable[[], float] = time.monotonic
    _failures: deque[float] = field(default_factory=deque, init=False, repr=False)

    def _forget_old(self) -> None:
        now = self.clock()
        while self._failures and now - self._failures[0] >= WINDOW_SECONDS:
            self._failures.popleft()

    def locked(self) -> bool:
        self._forget_old()
        return len(self._failures) >= MAX_FAILURES

    def failed(self) -> None:
        self._failures.append(self.clock())

    def succeeded(self) -> None:
        self._failures.clear()
