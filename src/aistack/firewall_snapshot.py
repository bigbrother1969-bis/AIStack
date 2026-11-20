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

Both commands are asked with `-c`, which adds the packet counters. The two
text files keep their form (the counters are removed from them, so the
reader of the rules is unchanged); what the counters say about refused
packets goes to `<dir>/firewall-refusals.jsonl`, one line per run, kept for
seven days (ADR-0028 T3b): the packets dropped by `DOCKER-USER`, by the
default policy of `INPUT`, by ufw's own rules and by any other chain. A
counter holds no address: the file says how many, never who. The boot
identifier lets a reader tell a reboot (counters start again) from a quiet
host.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HEADER = "# aistack-collected-at:"
COMMANDS = {
    "firewall-iptables.txt": "iptables-save",
    "firewall-ip6tables.txt": "ip6tables-save",
}


REFUSALS = "firewall-refusals.jsonl"
KEEP = timedelta(days=7)
BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
_RULE_COUNTER = re.compile(r"^\[(\d+):\d+\] ", re.MULTILINE)
_POLICY_COUNTER = re.compile(r"^(:\S+ \S+) \[\d+:\d+\]", re.MULTILINE)
_COUNTED_RULE = re.compile(r"^\[(\d+):\d+\] -A (\S+) .*-j (DROP|REJECT)\b", re.MULTILINE)
_POLICY = re.compile(r"^:(\S+) (\S+) \[(\d+):\d+\]", re.MULTILINE)


def strip_counters(text: str) -> str:
    """The text `iptables-save` gives without `-c`: the reader of the rules never saw counters."""

    return _POLICY_COUNTER.sub(r"\1 [0:0]", _RULE_COUNTER.sub("", text))


def _filter_table(text: str) -> str:
    kept, current = [], "filter"
    for line in text.splitlines():
        if line.startswith("*"):
            current = line[1:].strip()
        elif current == "filter":
            kept.append(line)
    return "\n".join(kept)


def refusals(text: str) -> dict[str, int]:
    """
    Packets refused, from one `iptables-save -c` reading of the `filter`
    table: the DROP and REJECT rules by chain family, and the default
    policy of INPUT when it drops.
    """

    table = _filter_table(text)
    counts = {"docker_user": 0, "input_policy": 0, "ufw": 0, "other": 0}

    for packets, chain, _ in _COUNTED_RULE.findall(table):
        family = "docker_user" if chain.startswith("DOCKER-USER") else "ufw" if chain.startswith(("ufw-", "ufw6-")) else "other"
        counts[family] += int(packets)

    for chain, policy, packets in _POLICY.findall(table):
        if chain == "INPUT" and policy == "DROP":
            counts["input_policy"] += int(packets)

    return counts


def _boot_id() -> str:
    try:
        return BOOT_ID.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _append_refusals(path: Path, record: dict[str, object], now: datetime, owner: tuple[int, int]) -> None:
    kept: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                at = datetime.fromisoformat(str(json.loads(line).get("at")))
            except (ValueError, AttributeError):
                continue
            if now - at <= KEEP:
                kept.append(line)
    except OSError:
        pass
    kept.append(json.dumps(record, sort_keys=True))
    _write(path, "\n".join(kept) + "\n", owner)


def _save(command: str) -> str | None:
    try:
        result = subprocess.run([command, "-c"], capture_output=True, text=True, timeout=30, check=False)
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
    drops: dict[str, int] = {}

    for name, command in COMMANDS.items():
        text = _save(command)
        if text is None:
            (output / name).unlink(missing_ok=True)
            failed += 1
            print(f"{command}: no answer", file=sys.stderr)
            continue
        _write(output / name, f"{HEADER} {stamp}\n{strip_counters(text)}", owner)
        for family, packets in refusals(text).items():
            drops[family] = drops.get(family, 0) + packets

    if (output / "firewall-iptables.txt").exists():
        _append_refusals(
            output / REFUSALS,
            {"at": stamp, "boot": _boot_id(), "drops": drops},
            datetime.fromisoformat(stamp),
            owner,
        )

    # IPv6 may be absent on a host; IPv4 missing is a failure.
    return 1 if (output / "firewall-iptables.txt").exists() is False else 0


if __name__ == "__main__":
    sys.exit(main())
