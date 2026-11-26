#!/usr/bin/env python3
"""
aistack-boot-facts — what the host looks like since its last start
(`ADR-0032`, slice B1).

One file, the Python standard library only. Installed as
`/usr/local/sbin/aistack-boot-facts`, run as root every five minutes by
`aistack-boot-facts.timer` (and two minutes after a start).

    aistack-boot-facts --output <dir> [--probe LABEL=URL ...] [--ups NAME]

It writes `<dir>/boot-facts.json`: **facts, never a verdict**. When the host
started and for how long it has run, the units that failed, the file systems
that are mounted, each container with its state and health, how many rules
the `DOCKER-USER` chain holds, whether the KVM modules are loaded, whether
the previous run ended with a clean shutdown, what the UPS says, and the
HTTP status each declared probe answers. Judging them belongs to AIStack,
which knows what the owner declared a healthy start to be.

It reads and never acts: the commands it can run are the closed list
`COMMANDS` below, each with its arguments fixed here, none through a shell,
none built from what a file or a log says. It writes no address, no URL, no
user name and no line of a log: a reader learns which names are up or down,
not what they say. A probe is written under its label, never its URL.

Each source is read on its own: one that fails or is absent says so in
`sources` and does not stop the others, so a reader never takes a silent
source for a healthy one. Nothing is changed on the host; the file is
replaced whole at every run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUTPUT_NAME = "boot-facts.json"
MAX_ITEMS = 400
PROBE_TIMEOUT = 5
COMMAND_TIMEOUT = 30

# Every command the unit may run. The arguments are fixed; `{ups}` is the
# only value filled in, and it comes from the unit's own configuration.
COMMANDS: dict[str, tuple[str, ...]] = {
    "failed_units": ("systemctl", "--failed", "--no-legend", "--plain", "--no-pager"),
    "containers": ("docker", "ps", "-a", "--format", "{{.Names}}\t{{.State}}\t{{.Status}}"),
    "docker_user": ("iptables", "-w", "2", "-S", "DOCKER-USER"),
    "previous_boot": ("journalctl", "--no-pager", "-o", "cat", "-b", "-1", "-n", "200"),
    "ups": ("upsc", "{ups}"),
}

# What a file system that is not a disk, a share or a mounted folder looks like.
PSEUDO_FILESYSTEMS = frozenset(
    (
        "proc", "sysfs", "devtmpfs", "devpts", "tmpfs", "cgroup", "cgroup2", "overlay", "securityfs",
        "debugfs", "tracefs", "configfs", "fusectl", "mqueue", "hugetlbfs", "pstore", "bpf", "autofs",
        "binfmt_misc", "efivarfs", "nsfs", "ramfs", "squashfs", "rpc_pipefs", "selinuxfs", "fuse.lxcfs",
        "nfsd", "fuse.gvfsd-fuse", "fuse.portal",
    )
)
_CLEAN_END = re.compile(r"Reached target .*(Power-Off|Reboot|Halt)|Shutting down\.|Journal stopped", re.IGNORECASE)
_HEALTH = re.compile(r"\((healthy|unhealthy|health: starting)\)")
_OCTAL = re.compile(r"\\([0-7]{3})")


def _run(name: str, ups: str = "") -> str:
    """Run one command of the closed list; a failure raises an `OSError` that says why."""

    template = COMMANDS[name]
    command = [ups if part == "{ups}" else part for part in template]

    if shutil.which(command[0]) is None:
        raise OSError(f"{command[0]} not found")

    result = subprocess.run(command, capture_output=True, text=True, timeout=COMMAND_TIMEOUT, check=False)

    if result.returncode != 0:
        stderr = result.stderr.strip().splitlines()
        raise OSError(stderr[-1] if stderr else f"{command[0]} failed")

    return result.stdout


def boot_facts(now: datetime, uptime_text: str, boot_id: str) -> dict[str, object]:
    """When the host started, from how long it has run (never from the journal: a host with no clock lies there)."""

    seconds = int(float(uptime_text.split()[0]))

    return {
        "booted_at": (now - timedelta(seconds=seconds)).isoformat(timespec="seconds"),
        "uptime_seconds": seconds,
        "boot_id": boot_id.strip(),
    }


def failed_units(text: str) -> list[str]:
    names = [line.split()[0] for line in text.splitlines() if line.strip()]

    return sorted(set(names))[:MAX_ITEMS]


def mounted(mountinfo: str) -> list[str]:
    """Where a real file system is mounted: a disk, a share, a folder; not a kernel or container one."""

    found: set[str] = set()

    for line in mountinfo.splitlines():
        before, separator, after = line.partition(" - ")
        fields = before.split()

        if not separator or len(fields) < 5 or not after.split():
            continue

        if after.split()[0] in PSEUDO_FILESYSTEMS:
            continue

        found.add(_OCTAL.sub(lambda match: chr(int(match.group(1), 8)), fields[4]))

    return sorted(found)[:MAX_ITEMS]


def _host_mountinfo(proc: Path) -> str:
    """
    The host's mounts, as the first process sees them. The unit's own view
    (`self`) also shows what its sandbox adds (its output folder, a private
    `/var/tmp`), which the host does not have; it is the fallback only.
    """

    try:
        return (proc / "1/mountinfo").read_text(encoding="utf-8")
    except OSError:
        return (proc / "self/mountinfo").read_text(encoding="utf-8")


def containers(text: str) -> list[dict[str, str]]:
    found = []

    for line in text.splitlines():
        parts = line.split("\t")

        if len(parts) < 3 or not parts[0]:
            continue

        health = _HEALTH.search(parts[2])
        found.append(
            {
                "name": parts[0],
                "state": parts[1],
                "health": {"health: starting": "starting"}.get(health.group(1), health.group(1)) if health else "none",
            }
        )

    return sorted(found, key=lambda item: item["name"])[:MAX_ITEMS]


def docker_user_rules(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("-A DOCKER-USER"))


def previous_boot_ended_cleanly(text: str) -> bool:
    """Whether the end of the previous run says it was shut down; `False` for a journal that just stops."""

    return any(_CLEAN_END.search(line) for line in text.splitlines()[-60:])


def ups_status(text: str) -> str:
    for line in text.splitlines():
        key, _, value = line.partition(":")

        if key.strip() == "ups.status":
            return value.strip()[:40]

    raise OSError("no ups.status")


def probe(url: str) -> int:
    """The HTTP status a URL answers, `0` when nothing answers. Redirections are not followed."""

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            return None

    opener = urllib.request.build_opener(_NoRedirect)

    try:
        with opener.open(url, timeout=PROBE_TIMEOUT) as answer:
            return int(answer.status)
    except urllib.error.HTTPError as error:
        return int(error.code)
    except (urllib.error.URLError, OSError, ValueError):
        return 0


def parse_probes(values: list[str]) -> dict[str, str]:
    """`label=url` pairs, from the command line and `AISTACK_BOOT_PROBES` (comma-separated)."""

    found: dict[str, str] = {}

    for value in values:
        for part in value.split(","):
            if not part.strip():
                continue

            label, separator, url = part.strip().partition("=")

            if not separator or not label or not url.startswith(("http://", "https://")):
                raise ValueError(part.strip().split("=")[0])

            found[label] = url

    return found


def collect(
    now: datetime,
    probes: dict[str, str],
    ups: str,
    *,
    proc: Path = Path("/proc"),
    probe_one=probe,  # type: ignore[no-untyped-def]
) -> dict[str, object]:
    sources: dict[str, str] = {}
    report: dict[str, object] = {"collected_at": now.isoformat(timespec="seconds")}

    def read(name: str, build) -> None:  # type: ignore[no-untyped-def]
        try:
            report[name] = build()
            sources[name] = "ok"
        except (OSError, ValueError, IndexError, subprocess.TimeoutExpired) as error:
            sources[name] = f"error: {str(error)[:120]}"

    read(
        "boot",
        lambda: boot_facts(
            now,
            (proc / "uptime").read_text(encoding="utf-8"),
            (proc / "sys/kernel/random/boot_id").read_text(encoding="utf-8"),
        ),
    )
    read("failed_units", lambda: failed_units(_run("failed_units")))
    read("mounts", lambda: mounted(_host_mountinfo(proc)))
    read("containers", lambda: containers(_run("containers")))
    read("docker_user_rules", lambda: docker_user_rules(_run("docker_user")))
    read("kvm_modules", lambda: any(line.startswith(("kvm ", "kvm_intel ", "kvm_amd ")) for line in (proc / "modules").read_text(encoding="utf-8").splitlines()))
    read("previous_boot_clean", lambda: previous_boot_ended_cleanly(_run("previous_boot")))

    if ups:
        read("ups", lambda: ups_status(_run("ups", ups)))
    else:
        sources["ups"] = "absent"

    if probes:
        report["probes"] = {label: probe_one(url) for label, url in sorted(probes.items())}
        sources["probes"] = "ok"
    else:
        sources["probes"] = "absent"

    report["sources"] = sources

    return report


def _write(path: Path, text: str, owner: tuple[int, int]) -> None:
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        handle.write(text)
        temporary = Path(handle.name)

    os.chmod(temporary, 0o644)
    os.chown(temporary, *owner)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the facts of the host since its last start.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--probe", action="append", default=[], help="LABEL=URL: the HTTP status it answers is written under LABEL")
    parser.add_argument("--ups", default=os.environ.get("AISTACK_BOOT_UPS", ""), help="the UPS name for upsc, e.g. apc@localhost")
    arguments = parser.parse_args()

    try:
        probes = parse_probes([*arguments.probe, os.environ.get("AISTACK_BOOT_PROBES", "")])
    except ValueError as error:
        print(f"not a probe (LABEL=http://...): {error}", file=sys.stderr)
        return 2

    output: Path = arguments.output
    output.mkdir(parents=True, exist_ok=True)
    status = output.stat()
    report = collect(datetime.now(timezone.utc), probes, arguments.ups)
    _write(output / OUTPUT_NAME, json.dumps(report, sort_keys=True, indent=1) + "\n", (status.st_uid, status.st_gid))

    return 0


if __name__ == "__main__":
    sys.exit(main())
