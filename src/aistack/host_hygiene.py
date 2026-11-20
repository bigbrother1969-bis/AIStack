#!/usr/bin/env python3
"""
aistack-host-hygiene — what the host says about its packages and its
sensitive files (`ADR-0028`, T2c).

One file, the Python standard library only. Installed as
`/usr/local/sbin/aistack-host-hygiene`, run as root once an hour by
`aistack-host-hygiene.timer`.

    aistack-host-hygiene --output <dir> [--glob PATTERN ...]

It writes `<dir>/host-packages.txt` and `<dir>/host-files.txt`, each under
a first line that dates it.

*Packages.* `apt-get -s dist-upgrade` simulates and changes nothing; it
reads the package lists already on the disk and asks no network. The file
says how many upgrades wait, which of them come from a security
archive, how old the package lists are and since when a reboot is
required. The container that assesses the host has no `apt` and sees none
of this.

*Files.* For each file matching a pattern (SSH keys, `.env` files,
Docker and cloudflared credentials, the UPS accounts), one line: octal
mode, owner, group, path. Only what `stat` says; **never a file's content**.
Only root can walk `/root` and the other users' homes, which is why this
runs on the host and as root. `--glob` adds patterns to the default ones.

A command that fails removes its file, so a reader never judges a stale
answer as a current one. Nothing is changed on the host.
"""

from __future__ import annotations

import argparse
import glob
import grp
import os
import pwd
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HEADER = "# aistack-collected-at:"
PACKAGES = "host-packages.txt"
FILES = "host-files.txt"
REBOOT_FLAG = Path("/var/run/reboot-required")
LISTS_STAMP = Path("/var/lib/apt/periodic/update-success-stamp")
LISTS_DIRECTORY = Path("/var/lib/apt/lists")

# Files whose content is a secret or whose rights decide who controls the host.
DEFAULT_GLOBS = (
    "/etc/ssh/ssh_host_*_key",
    "/root/.ssh/id_*",
    "/home/*/.ssh/id_*",
    "/root/.docker/config.json",
    "/home/*/.docker/config.json",
    "/etc/cloudflared/*.json",
    "/etc/cloudflared/cert.pem",
    "/etc/nut/upsd.users",
    "/etc/nut/upsmon.conf",
    "/srv/*/.env",
    "/srv/*/.env.*",
    "/srv/*/*/.env",
    "/srv/*/*/.env.*",
    "/home/*/.env",
    "/home/*/*/.env",
    "/home/*/*/.env.*",
    "/opt/*/.env",
)
SKIPPED_SUFFIXES = (".pub", ".example", ".sample", ".dist", ".template")

_INST = re.compile(r"^Inst (\S+) (?:\[([^\]]*)\] )?\((\S+) ([^)]*)\)")


def parse_simulation(text: str) -> list[tuple[str, str, str, bool]]:
    """
    The upgrades `apt-get -s` plans: (package, installed version, new
    version, comes from a security archive).
    """

    found: list[tuple[str, str, str, bool]] = []
    for line in text.splitlines():
        match = _INST.match(line)
        if match is None:
            continue
        name, old, new, origins = match.groups()
        if old is None:
            continue  # a new dependency, not an upgrade of something installed
        found.append((name, old, new, "security" in origins.lower()))
    return found


def _simulate() -> str | None:
    try:
        result = subprocess.run(
            ["apt-get", "-s", "-o", "Debug::NoLocking=1", "dist-upgrade"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds")


def _lists_updated() -> str:
    if LISTS_STAMP.exists():
        return _iso(LISTS_STAMP.stat().st_mtime)
    try:
        newest = max(item.stat().st_mtime for item in LISTS_DIRECTORY.iterdir() if item.is_file())
    except (OSError, ValueError):
        return "unknown"
    return _iso(newest)


def packages_text() -> str | None:
    simulation = _simulate()
    if simulation is None:
        return None
    upgrades = parse_simulation(simulation)
    lines = [
        f"upgradable: {len(upgrades)}",
        f"security: {sum(1 for item in upgrades if item[3])}",
        f"reboot-required-since: {_iso(REBOOT_FLAG.stat().st_mtime) if REBOOT_FLAG.exists() else 'no'}",
        f"lists-updated: {_lists_updated()}",
    ]
    lines += [f"package: {name} {old} {new} {'security' if secure else 'other'}" for name, old, new, secure in upgrades]
    return "\n".join(lines) + "\n"


def _name(table, key: int, field: str) -> str:
    try:
        return str(getattr(table(key), field))
    except KeyError:
        return str(key)


def files_text(patterns: tuple[str, ...]) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if path in seen or path.endswith(SKIPPED_SUFFIXES):
                continue
            seen.add(path)
            try:
                status = os.lstat(path)
            except OSError:
                continue
            if not stat.S_ISREG(status.st_mode):
                continue
            mode = stat.S_IMODE(status.st_mode)
            owner = _name(pwd.getpwuid, status.st_uid, "pw_name")
            group = _name(grp.getgrgid, status.st_gid, "gr_name")
            lines.append(f"{mode:04o} {owner} {group} {path}")
    return "\n".join(lines) + ("\n" if lines else "")


def _write(path: Path, text: str, owner: tuple[int, int]) -> None:
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.chmod(temporary, 0o644)
    os.chown(temporary, *owner)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write what the host says about its packages and its sensitive files.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--glob", action="append", default=[], help="another file pattern to read the rights of")
    arguments = parser.parse_args()

    output: Path = arguments.output
    output.mkdir(parents=True, exist_ok=True)
    status = output.stat()
    owner = (status.st_uid, status.st_gid)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    packages = packages_text()
    if packages is None:
        (output / PACKAGES).unlink(missing_ok=True)
        print("apt-get: no answer", file=sys.stderr)
    else:
        _write(output / PACKAGES, f"{HEADER} {stamp}\n{packages}", owner)

    _write(output / FILES, f"{HEADER} {stamp}\n{files_text(DEFAULT_GLOBS + tuple(arguments.glob))}", owner)

    # A host with no apt (not a Debian family) has no package reading; the files are still read.
    return 0


if __name__ == "__main__":
    sys.exit(main())
