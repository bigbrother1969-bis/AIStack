#!/usr/bin/env python3
"""
aistack-firewall-snapshot — what the host's firewall says (`ADR-0028`).

One file, the Python standard library only. Installed as
`/usr/local/sbin/aistack-firewall-snapshot`, run as root every ten
minutes by `aistack-firewall-snapshot.timer`.

    aistack-firewall-snapshot --output <dir>

It asks `iptables-save` and `ip6tables-save`, which only read, and writes
their answer to `<dir>/firewall-iptables.txt` and
`<dir>/firewall-ip6tables.txt`, each under a first line that dates it.
The container that assesses the host has no `iptables`, and a reading
made from its own network namespace would say "no rule" about a host that
has some. This unit runs in the host's namespace, changes no rule, and
writes nowhere else. A command that fails removes its file, so a reader
never judges a stale answer as a current one.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HEADER = "# aistack-collected-at:"
COMMANDS = {
    "firewall-iptables.txt": "iptables-save",
    "firewall-ip6tables.txt": "ip6tables-save",
}


def _save(command: str) -> str | None:
    try:
        result = subprocess.run([command], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 and result.stdout.strip() else None


def _write(path: Path, text: str, owner: tuple[int, int]) -> None:
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.chmod(temporary, 0o644)
    os.chown(temporary, *owner)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write what the host's firewall says.")
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()

    output: Path = arguments.output
    output.mkdir(parents=True, exist_ok=True)
    status = output.stat()
    owner = (status.st_uid, status.st_gid)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    failed = 0

    for name, command in COMMANDS.items():
        text = _save(command)
        if text is None:
            (output / name).unlink(missing_ok=True)
            failed += 1
            print(f"{command}: no answer", file=sys.stderr)
            continue
        _write(output / name, f"{HEADER} {stamp}\n{text}", owner)

    # IPv6 may be absent on a host; IPv4 missing is a failure.
    return 1 if (output / "firewall-iptables.txt").exists() is False else 0


if __name__ == "__main__":
    sys.exit(main())
