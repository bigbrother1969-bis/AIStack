"""
What a new installation still has to declare before it is used
(`ADR-0017` § 4).

A configuration directory filled by `config_init` holds the reference
host's values: its host name, its ports, its identity provider, its
public address. AIStack starts on them — it never fails on them — and
says what to declare first, until it is declared.

**Which declarations are still the shipped ones.** `config_init` keeps,
next to the files it copies, the fingerprint of each copy
(`.shipped.json`); a first declaration whose file still has that
fingerprint was never edited. A file the owner put in the directory
himself — GIGABYTE's own, at its move — was never copied, so it is
never reported: comparing with the shipped values instead would report
the reference host as unconfigured on the reference host.

**Which secrets are missing.** Read from the environment the web
process started with: no client ID or secret, no sign-in.

Without a configuration directory (a git installation), only the
secrets are checked.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

SHIPPED_RECORD = ".shipped.json"

INSTANCE = "instance"
AUTHENTICATION = "authentication"
SIGN_IN_SECRETS = "sign_in_secrets"
FALLBACK_SECRET = "fallback_secret"

# The declarations nothing works without, in the order to edit them.
FIRST_DECLARATIONS = {
    INSTANCE: "instance_config.yml",
    AUTHENTICATION: "authentication.yml",
}


@dataclass(frozen=True)
class Pending:
    """One thing still to declare: `key` names it, `required` says
    whether AIStack is unusable without it (the fallback account is
    recommended, not required)."""

    key: str
    required: bool


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_record(directory: Path) -> dict[str, str]:
    try:
        record = json.loads((directory / SHIPPED_RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(name): str(value) for name, value in record.items()} if isinstance(record, dict) else {}


def remember_copies(directory: Path, names: list[str]) -> None:
    """Record the fingerprint of each file `config_init` just copied."""

    if not names:
        return
    record = read_record(directory)
    for name in names:
        record[name] = fingerprint(directory / name)
    # Six services start together and each runs `config_init`: write
    # whole, never half a file another one would read.
    temporary = directory / f"{SHIPPED_RECORD}.{os.getpid()}"
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(directory / SHIPPED_RECORD)


def still_shipped(directory: Path, name: str) -> bool:
    """`name` was copied by `config_init` and never edited since."""

    recorded = read_record(directory).get(name)
    path = directory / name
    return recorded is not None and path.is_file() and fingerprint(path) == recorded


def pending(
    directory: Path | None,
    *,
    client_id: str,
    client_secret: str,
    local_admin_hash: str,
) -> list[Pending]:
    """What is still to declare, in the order to do it."""

    found = []
    if directory is not None:
        for key, name in FIRST_DECLARATIONS.items():
            if still_shipped(directory, name):
                found.append(Pending(key, required=True))
    if not client_id or not client_secret:
        found.append(Pending(SIGN_IN_SECRETS, required=True))
    if not local_admin_hash:
        found.append(Pending(FALLBACK_SECRET, required=False))
    return found


def needs_setup(items: list[Pending]) -> bool:
    return any(item.required for item in items)
