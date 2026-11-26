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
    # A Raspberry's power and temperature flags, and whether its clock was set by the network.
    "throttled": ("vcgencmd", "get_throttled"),
    "clock": ("timedatectl", "show", "-p", "NTPSynchronized", "--value"),
    # B5a: what the kernel said of its disks since the start, and what a declared database said of its recovery.
    "kernel_errors": ("journalctl", "--no-pager", "-o", "cat", "-k", "-b", "-p", "err"),
    "database_logs": ("docker", "logs", "--since", "{since}", "{name}"),
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
# What the kernel says of a disk or a file system that fails; only how many lines say it is written.
_DISK_ERROR = re.compile(
    r"I/O error|EXT4-fs error|XFS .*(error|corruption)|BTRFS .*error|blk_update_request|"
    r"ata\d+(\.\d+)?: .*(error|failed|exception)|nvme\d+.*(timeout|error)|mmcblk\d+.*(error|timeout)|"
    r"Remounting filesystem read-only|critical medium error",
    re.IGNORECASE,
)
# What a database says when it starts again after a stop that was not clean.
_RECOVERY = re.compile(
    r"crash recovery|not properly shut down|was interrupted|automatic recovery in progress|redo starts at|"
    r"recovering after unclean shutdown|starting recovery",
    re.IGNORECASE,
)
_UPS_STOP = re.compile(
    r"upsmon.*(shutdown|FSD|battery)|automatic power-fail shutdown|forced shutdown|UPS .*(on battery|low battery)",
    re.IGNORECASE,
)
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,60}$")
_HEALTH = re.compile(r"\((healthy|unhealthy|health: starting)\)")
_OCTAL = re.compile(r"\\([0-7]{3})")


def _run(which: str, ups: str = "", /, **values: str) -> str:
    """
    Run one command of the closed list; a failure raises an `OSError` that says why.

    Only `{ups}`, `{since}` and `{name}` are filled in, from the unit's own configuration
    and the start time it computed; a `{name}` that is not a plain container name is refused.
    A container's logs come out on both streams, so both are read.
    """

    template = COMMANDS[which]
    fill = {"{ups}": ups, **{"{" + key + "}": value for key, value in values.items()}}

    if "name" in values and not _NAME.match(values["name"]):
        raise OSError("not a container name")

    command = [fill.get(part, part) for part in template]

    if shutil.which(command[0]) is None:
        raise OSError(f"{command[0]} not found")

    merged = which == "database_logs"
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merged else subprocess.PIPE,
        text=True,
        timeout=COMMAND_TIMEOUT,
        check=False,
    )

    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip().splitlines()
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


def stop_reason(text: str) -> str:
    """Why the previous run stopped, from the end of its journal: `ups`, `requested` (a shutdown or reboot), or `unknown`."""

    tail = text.splitlines()[-60:]

    if any(_UPS_STOP.search(line) for line in tail):
        return "ups"

    if any(_CLEAN_END.search(line) for line in tail):
        return "requested"

    return "unknown"


def disk_error_lines(text: str) -> int:
    """How many kernel lines say a disk or a file system failed; never the lines."""

    return sum(1 for line in text.splitlines() if _DISK_ERROR.search(line))


def recovery_lines(text: str) -> int:
    """How many lines of a database's log say it recovered after the start; never the lines."""

    return sum(1 for line in text.splitlines() if _RECOVERY.search(line))


def memory_pressure(text: str) -> float:
    """The 5-minute average of `some` stalls (PSI), in percent."""

    for line in text.splitlines():
        if line.startswith("some "):
            for part in line.split():
                if part.startswith("avg300="):
                    return float(part.partition("=")[2])

    raise OSError("no memory pressure value")


def swap_used_percent(meminfo: str) -> int:
    """The share of swap in use (zram is swap too); 0 when the host has none."""

    values = {line.split(":")[0]: int(line.split()[1]) for line in meminfo.splitlines() if ":" in line and len(line.split()) > 1}
    total = values.get("SwapTotal", 0)

    return 0 if total <= 0 else round(100 * (total - values.get("SwapFree", 0)) / total)


def ups_status(text: str) -> str:
    for line in text.splitlines():
        key, _, value = line.partition(":")

        if key.strip() == "ups.status":
            return value.strip()[:40]

    raise OSError("no ups.status")


def throttled_flags(text: str) -> int:
    """The flags `vcgencmd get_throttled` says (`throttled=0x50005`); the low four bits are *now*, the next ones *since the start*."""

    key, _, value = text.strip().partition("=")

    if key != "throttled":
        raise OSError("no throttled value")

    try:
        return int(value, 16)
    except ValueError as error:
        raise OSError("throttled is not a number") from error


def clock_synchronized(text: str) -> bool:
    """Whether the clock was set by the network (`yes`); a host with no clock of its own is `no` until it was."""

    answer = text.strip().lower()

    if answer not in ("yes", "no"):
        raise OSError("no NTPSynchronized value")

    return answer == "yes"


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


def _recoveries(names: tuple[str, ...], report: dict[str, object]) -> dict[str, int]:
    """The recovery lines of each declared database since the start; one that cannot be read is left out, and all of them failing is a failure."""

    boot = report.get("boot")
    since = boot["booted_at"] if isinstance(boot, dict) and isinstance(boot.get("booted_at"), str) else ""

    if not since:
        raise OSError("the start time is not known")

    found: dict[str, int] = {}
    reason = ""

    for name in names:
        try:
            found[name] = recovery_lines(_run("database_logs", since=since, name=name))
        except (OSError, subprocess.TimeoutExpired) as error:
            reason = f"{name}: {str(error)[:80]}"

    if not found:
        raise OSError(reason or "no database")

    return found


def collect(
    now: datetime,
    probes: dict[str, str],
    ups: str,
    databases: tuple[str, ...] = (),
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
    read("clock_synced", lambda: clock_synchronized(_run("clock")))
    read("stop_reason", lambda: stop_reason(_run("previous_boot")))
    read("kernel_disk_errors", lambda: disk_error_lines(_run("kernel_errors")))
    read("memory_pressure", lambda: memory_pressure((proc / "pressure/memory").read_text(encoding="utf-8")))
    read("swap_used_percent", lambda: swap_used_percent((proc / "meminfo").read_text(encoding="utf-8")))

    if databases:
        read("database_recovery", lambda: _recoveries(databases, report))
    else:
        sources["database_recovery"] = "absent"

    # Only a Raspberry has the command; elsewhere the source is absent, not failed.
    if shutil.which(COMMANDS["throttled"][0]) is None:
        sources["throttled"] = "absent"
    else:
        read("throttled", lambda: throttled_flags(_run("throttled")))

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
    parser.add_argument("--database", action="append", default=[], help="a container whose log is read for its recovery after the start (AISTACK_BOOT_DATABASES, comma-separated)")
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
    names = tuple(dict.fromkeys(name.strip() for value in [*arguments.database, os.environ.get("AISTACK_BOOT_DATABASES", "")] for name in value.split(",") if name.strip()))

    if not all(_NAME.match(name) for name in names):
        print("not a container name in --database / AISTACK_BOOT_DATABASES", file=sys.stderr)
        return 2

    report = collect(datetime.now(timezone.utc), probes, arguments.ups, names)
    _write(output / OUTPUT_NAME, json.dumps(report, sort_keys=True, indent=1) + "\n", (status.st_uid, status.st_gid))

    return 0


if __name__ == "__main__":
    sys.exit(main())
