#!/usr/bin/env python3
"""
aistack-host-logs — what the host's logs say about who tried to get in
(`ADR-0028`, T3c).

One file, the Python standard library only. Installed as
`/usr/local/sbin/aistack-host-logs`, run as root once an hour by
`aistack-host-logs.timer`.

    aistack-host-logs --output <dir> [--vpn CIDR ...] [--lan CIDR ...] [--npm-logs DIR]

It writes `<dir>/host-logs.json`: **counts over the last 24 hours, and
nothing else**. For each origin class (the LAN, the VPN, outside), how many
SSH logins failed and how many named a user the host does not have; how
many packets `DOCKER-USER` refused and logged; and, when a Nginx Proxy
Manager keeps its logs on the host, per virtual host how many requests
ended in 2xx, 3xx, 4xx and 5xx, how many asked for a probe (`/.env`,
`/.git`: nobody else asks) and for an application path (`wp-login.php`,
`xmlrpc.php`…), and how many of each were answered with a success (2xx). It never writes an address, a
path, a user name, a line of a log or a header: a reader of the file
learns how many and from what kind of network, not who or what.

The classes: an address in `--vpn` is the VPN; otherwise an address in
`--lan` (by default the private ranges) is the LAN; otherwise outside; an
address that cannot be read is `unknown`. `--vpn` and `--lan` can also be
given by `AISTACK_LOGS_VPN` and `AISTACK_LOGS_LAN` (comma-separated).

Each source is read on its own: one that fails or is absent says so in
`sources` and does not stop the others, so a reader never takes a
silent source for a quiet host. Nothing is changed on the host; the file
is replaced whole at every run.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUTPUT_NAME = "host-logs.json"
WINDOW = timedelta(hours=24)
# A busy proxy writes a lot: only the end of a file is read.
MAX_BYTES = 64 * 1024 * 1024
MAX_VHOSTS = 200
VHOST_KEYS = ("2xx", "3xx", "4xx", "5xx", "probes", "probes_ok", "app_paths", "app_paths_ok")
CLASSES = ("lan", "vpn", "outside", "unknown")
DEFAULT_LAN = (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16", "127.0.0.0/8",
    "fc00::/7", "fe80::/10", "::1/128",
)
# Matched in lower case against the request path; the path itself is never kept.
# A probe is asked for by scanners and by nobody else: no service has a reason to answer it.
PROBE_SIGNATURES = ("/.env", "/.git", "/../", "%2e%2e")
# An application path is asked for by scanners too, and by the person who uses the application
# (a WordPress login): it is counted apart, and what matters is that it answers.
APP_SIGNATURES = ("wp-login.php", "wp-admin", "xmlrpc.php", "phpmyadmin", "/cgi-bin")
MONTHS = {name: number for number, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), start=1)}

_SSH_FAILED = re.compile(r"Failed (?:password|publickey|keyboard-interactive/pam|none) for (?:invalid user )?.+? from (\S+)")
_SSH_INVALID = re.compile(r"Invalid user .*? from (\S+)")
_KERNEL = re.compile(r"DOCKER-USER-REFUSE .*?SRC=(\S+)")
_NPM = re.compile(
    r'^\[(?P<time>[^\]]+)\] (?P<rest>.*?) (?P<status>\d{3}) - [A-Z]+ https? (?P<host>\S+) "(?P<uri>[^"]*)" \[Client (?P<ip>[^\]]+)\]'
)
_TIME = re.compile(r"(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2}) ([+-])(\d{2})(\d{2})")


def networks(values: list[str]) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    found = []
    for value in values:
        for part in value.split(","):
            if part.strip():
                found.append(ipaddress.ip_network(part.strip(), strict=False))
    return found


def origin(address: str, vpn: list, lan: list) -> str:
    try:
        ip = ipaddress.ip_address(address.strip("[]"))
    except ValueError:
        return "unknown"
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if any(ip.version == net.version and ip in net for net in vpn):
        return "vpn"
    if any(ip.version == net.version and ip in net for net in lan):
        return "lan"
    return "outside"


def _empty() -> dict[str, int]:
    return {name: 0 for name in CLASSES}


def _journal(arguments: list[str], since: datetime) -> list[str]:
    command = ["journalctl", "--no-pager", "-o", "cat", "--since", since.strftime("%Y-%m-%d %H:%M:%S UTC"), *arguments]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0:
        raise OSError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "journalctl failed")
    return result.stdout.splitlines()


def ssh_counts(lines: list[str], vpn: list, lan: list) -> dict[str, dict[str, int]]:
    failed, invalid = _empty(), _empty()
    for line in lines:
        match = _SSH_FAILED.search(line)
        if match:
            failed[origin(match.group(1), vpn, lan)] += 1
            continue
        match = _SSH_INVALID.search(line)
        if match:
            invalid[origin(match.group(1), vpn, lan)] += 1
    return {"failed": failed, "invalid_user": invalid}


def kernel_counts(lines: list[str], vpn: list, lan: list) -> dict[str, dict[str, int]]:
    refused = _empty()
    for line in lines:
        match = _KERNEL.search(line)
        if match:
            refused[origin(match.group(1), vpn, lan)] += 1
    return {"docker_user_refuse": refused}


def _instant(text: str) -> datetime | None:
    match = _TIME.fullmatch(text.strip())
    if not match or match.group(2) not in MONTHS:
        return None
    day, month, year, hour, minute, second, sign, offset_h, offset_m = match.groups()
    zone = timezone(timedelta(hours=int(offset_h), minutes=int(offset_m)) * (1 if sign == "+" else -1))
    try:
        return datetime(int(year), MONTHS[month], int(day), int(hour), int(minute), int(second), tzinfo=zone)
    except ValueError:
        return None


def _tail_lines(path: Path) -> list[str]:
    with path.open("rb") as stream:
        size = stream.seek(0, os.SEEK_END)
        stream.seek(max(size - MAX_BYTES, 0))
        data = stream.read()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return lines[1:] if size > MAX_BYTES else lines


def npm_counts(directory: Path, since: datetime, vpn: list, lan: list) -> dict[str, object]:
    vhosts: dict[str, Counter[str]] = {}
    probes_by_origin, probes_ok_by_origin, app_by_origin = _empty(), _empty(), _empty()
    requests = 0

    for path in sorted([*directory.glob("*_access.log"), *directory.glob("*_access.log.1")]):
        for line in _tail_lines(path):
            match = _NPM.match(line)
            if not match:
                continue
            at = _instant(match.group("time"))
            if at is None or at < since:
                continue
            requests += 1
            host = match.group("host").lower()
            if host not in vhosts and len(vhosts) >= MAX_VHOSTS:
                host = "other"
            counter = vhosts.setdefault(host, Counter())
            status_class = f"{match.group('status')[0]}xx"
            counter[status_class] += 1
            uri = match.group("uri").lower()
            where = origin(match.group("ip"), vpn, lan)
            if any(signature in uri for signature in PROBE_SIGNATURES):
                counter["probes"] += 1
                probes_by_origin[where] += 1
                if status_class == "2xx":
                    counter["probes_ok"] += 1
                    probes_ok_by_origin[where] += 1
            elif any(signature in uri for signature in APP_SIGNATURES):
                counter["app_paths"] += 1
                app_by_origin[where] += 1
                if status_class == "2xx":
                    counter["app_paths_ok"] += 1

    return {
        "requests": requests,
        "vhosts": {
            host: {key: counter.get(key, 0) for key in VHOST_KEYS}
            for host, counter in sorted(vhosts.items())
        },
        "probes_by_origin": probes_by_origin,
        "probes_ok_by_origin": probes_ok_by_origin,
        "app_paths_by_origin": app_by_origin,
    }


def collect(now: datetime, vpn: list, lan: list, npm_logs: Path | None) -> dict[str, object]:
    since = now - WINDOW
    sources: dict[str, str] = {}
    report: dict[str, object] = {"collected_at": now.isoformat(timespec="seconds"), "window_hours": 24}

    for name, arguments, build in (
        ("ssh", ["_COMM=sshd"], ssh_counts),
        ("kernel", ["-k"], kernel_counts),
    ):
        try:
            report[name] = build(_journal(arguments, since), vpn, lan)
            sources[name] = "ok"
        except (OSError, subprocess.TimeoutExpired) as error:
            sources[name] = f"error: {str(error)[:120]}"

    if npm_logs is None or not npm_logs.is_dir():
        sources["npm"] = "absent"
    else:
        try:
            report["npm"] = npm_counts(npm_logs, since, vpn, lan)
            sources["npm"] = "ok"
        except OSError as error:
            sources["npm"] = f"error: {str(error)[:120]}"

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
    parser = argparse.ArgumentParser(description="Write how many logins and requests failed, by kind of network.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--vpn", action="append", default=[], help="the VPN's network, e.g. 10.0.0.0/24")
    parser.add_argument("--lan", action="append", default=[], help="the LAN's network (default: the private ranges)")
    parser.add_argument("--npm-logs", type=Path, default=None, help="the directory of Nginx Proxy Manager's logs")
    arguments = parser.parse_args()

    try:
        vpn = networks([*arguments.vpn, os.environ.get("AISTACK_LOGS_VPN", "")])
        lan = networks([*arguments.lan, os.environ.get("AISTACK_LOGS_LAN", "")]) or networks(list(DEFAULT_LAN))
    except ValueError as error:
        print(f"not a network: {error}", file=sys.stderr)
        return 2

    npm = arguments.npm_logs or (Path(os.environ["AISTACK_LOGS_NPM"]) if os.environ.get("AISTACK_LOGS_NPM") else None)

    output: Path = arguments.output
    output.mkdir(parents=True, exist_ok=True)
    status = output.stat()
    report = collect(datetime.now(timezone.utc), vpn, lan, npm)
    _write(output / OUTPUT_NAME, json.dumps(report, sort_keys=True, indent=1) + "\n", (status.st_uid, status.st_gid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
