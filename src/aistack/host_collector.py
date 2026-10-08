#!/usr/bin/env python3
"""
aistack-host-collector — what changes on a host (`ADR-0020`).

One file, the Python standard library only, so the same file runs on a
host that has no copy of AIStack. Installed as
`/usr/local/sbin/aistack-host-collector`, run as root every 15 minutes
by `aistack-host-collector.timer`; reads, never writes anywhere but its
output directory and its key.

    aistack-host-collector --host gigabyte --output <dir>

Each run appends to `<dir>/events.jsonl`, one JSON object per line:

- `package` — an install, upgrade, removal or purge read from
  `/var/log/dpkg.log*`, dated by the log;
- `apt` — an apt run read from `/var/log/apt/history.log*`: its
  command line, who asked, how many packages of each action;
- `file` — a watched file added, removed or modified: size, mode,
  owner, and a keyed fingerprint (HMAC-SHA-256 with the host's own key),
  never the content;
- `unit` — a systemd unit file whose state changed (enabled, disabled,
  masked…);
- `baseline` — the first run's count of what it found, instead of one
  event per existing file or unit.

The logs are read whole at the first run (every rotation still on
disk, compressed or not), then from where the last run stopped. What it
compares against lives in `<dir>/state/`; `<dir>/host.json` says when it
last ran. Everything it writes is given to the owner of `<dir>`, the
account AIStack reads it as.

A file `/etc/aistack-host-collector.conf` may add, one per line,
`watch = <directory>`, `glob = <pattern>` or `ignore = <pattern>`.
"""

from __future__ import annotations

import argparse
import fcntl
import fnmatch
import glob
import gzip
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COLLECTOR_VERSION = 1

DEFAULT_KEY = Path("/var/lib/aistack-host-collector/key")
DEFAULT_CONFIG = Path("/etc/aistack-host-collector.conf")
DEFAULT_LOGS = Path("/var/log")

DEFAULT_WATCH = ("/etc", "/usr/local/bin", "/usr/local/sbin", "/var/spool/cron/crontabs")
# The compose projects' own files, one and two levels under /srv and /opt.
_COMPOSE_NAMES = ("docker-compose*.yml", "docker-compose*.yaml", "compose*.yml", "compose*.yaml", ".env*")
DEFAULT_GLOBS = tuple(
    f"{root}/{depth}{name}"
    for root in ("/srv", "/opt")
    for depth in ("*/", "*/*/")
    for name in _COMPOSE_NAMES
)
# Files that change on their own, not by anyone's act.
DEFAULT_IGNORE = (
    "/etc/adjtime",
    "/etc/ld.so.cache",
    "/etc/.pwd.lock",
    "/etc/mtab",
    "*.swp",
    "*~",
)

UNIT_TYPES = "service,timer,socket,path"

_DPKG_LINE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (install|upgrade|remove|purge) (\S+) (\S+) (\S+)$"
)
_APT_ACTIONS = ("Install", "Reinstall", "Upgrade", "Downgrade", "Remove", "Purge")

Event = dict[str, Any]


# -- small helpers -----------------------------------------------------------

def _local_to_utc(text: str) -> str:
    """A log's local `YYYY-MM-DD HH:MM:SS` as an ISO instant in UTC."""

    moment = datetime.strptime(" ".join(text.split()), "%Y-%m-%d %H:%M:%S").astimezone()
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _owner_of(path: Path) -> tuple[int, int]:
    info = path.stat()
    return info.st_uid, info.st_gid


def _give(path: Path, owner: tuple[int, int] | None) -> None:
    if owner is not None and os.geteuid() == 0:
        os.chown(path, *owner)


def _write_json(path: Path, data: Any, owner: tuple[int, int] | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _give(path.parent, owner)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    _give(partial, owner)
    os.replace(partial, path)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_key(path: Path) -> bytes:
    """The host's fingerprint key, drawn at the first run, root only."""

    try:
        return path.read_bytes()
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        key = secrets.token_bytes(32)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(key)
        return key


def read_config(path: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {"watch": [], "glob": [], "ignore": []}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return found
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if "=" not in line:
            continue
        key, _, value = (part.strip() for part in line.partition("="))
        if key in found and value:
            found[key].append(value)
    return found


# -- logs --------------------------------------------------------------------

def _rotations(directory: Path, name: str) -> list[Path]:
    """`name.N.gz` … `name.1`, `name`: oldest first."""

    found = []
    for path in directory.glob(name + "*"):
        suffix = path.name[len(name):]
        match = re.fullmatch(r"(?:\.(\d+))?(\.gz)?", suffix)
        if match:
            found.append((-int(match.group(1) or 0), path))
    return [path for _, path in sorted(found)]


def _lines(path: Path) -> Iterator[str]:
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
                yield from stream
        else:
            with path.open(encoding="utf-8", errors="replace") as stream:
                yield from stream
    except OSError:
        return


def _after(cursor: dict[str, Any], at: str, signature: str) -> bool:
    """Not yet imported: later than the cursor, or at its instant and
    not among the lines already seen there."""

    last = cursor.get("at", "")
    return at > last or (at == last and signature not in cursor.get("seen", []))


def _advance(cursor: dict[str, Any], at: str, signature: str) -> None:
    if at > cursor.get("at", ""):
        cursor["at"], cursor["seen"] = at, [signature]
    elif at == cursor.get("at"):
        cursor.setdefault("seen", []).append(signature)


def dpkg_events(logs: Path, cursor: dict[str, Any], host: str) -> list[Event]:
    events = []
    for path in _rotations(logs, "dpkg.log"):
        for line in _lines(path):
            match = _DPKG_LINE.match(line.strip())
            if not match:
                continue
            when, action, package, before, after = match.groups()
            at = _local_to_utc(when)
            signature = hashlib.sha256(line.strip().encode()).hexdigest()[:16]
            if not _after(cursor, at, signature):
                continue
            _advance(cursor, at, signature)
            events.append({
                "at": at, "host": host, "kind": "package", "action": action, "package": package,
                "from": None if before == "<none>" else before,
                "to": None if after == "<none>" else after,
            })
    return events


def apt_events(logs: Path, cursor: dict[str, Any], host: str) -> list[Event]:
    events = []
    for path in _rotations(logs / "apt", "history.log"):
        block: dict[str, str] = {}
        for line in [*_lines(path), "\n"]:
            line = line.rstrip("\n")
            if line.strip():
                key, _, value = line.partition(": ")
                block[key.strip()] = value.strip()
                continue
            if "Start-Date" in block:
                at = _local_to_utc(block["Start-Date"])
                signature = hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()[:16]
                if _after(cursor, at, signature):
                    _advance(cursor, at, signature)
                    events.append({
                        "at": at, "host": host, "kind": "apt",
                        "ended": _local_to_utc(block["End-Date"]) if "End-Date" in block else None,
                        "commandline": block.get("Commandline", ""),
                        "requested_by": block.get("Requested-By", ""),
                        "counts": {
                            action.lower(): len(re.findall(r"\), |\)$", block[action]))
                            for action in _APT_ACTIONS if action in block
                        },
                    })
            block = {}
    return events


# -- files ---------------------------------------------------------------------

def _ignored(path: str, ignore: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in ignore)


def watched_paths(watch: Iterable[str], globs: Iterable[str], ignore: list[str]) -> list[str]:
    found: set[str] = set()
    for root in watch:
        for directory, subdirectories, files in os.walk(root, followlinks=False):
            subdirectories[:] = [d for d in subdirectories if not _ignored(os.path.join(directory, d), ignore)]
            for name in files:
                found.add(os.path.join(directory, name))
            # A symbolic link to a directory is a file here, not followed.
            for name in list(subdirectories):
                full = os.path.join(directory, name)
                if os.path.islink(full):
                    found.add(full)
                    subdirectories.remove(name)
    for pattern in globs:
        found.update(path for path in glob.glob(pattern) if os.path.isfile(path) or os.path.islink(path))
    return sorted(path for path in found if not _ignored(path, ignore))


def _fingerprint(path: str, key: bytes) -> str | None:
    digest = hmac.new(key, digestmod=hashlib.sha256)
    try:
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1 << 16), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()[:32]


def describe(path: str, key: bytes, previous: dict[str, Any] | None) -> dict[str, Any] | None:
    """What is kept of one file: never its content."""

    try:
        info = os.lstat(path)
    except OSError:
        return None
    meta: dict[str, Any] = {
        "mode": oct(stat.S_IMODE(info.st_mode)),
        "owner": f"{info.st_uid}:{info.st_gid}",
        "_stamp": [info.st_size, info.st_mtime_ns, info.st_ino],
    }
    if stat.S_ISLNK(info.st_mode):
        meta["link"] = os.readlink(path)
        return meta
    if not stat.S_ISREG(info.st_mode):
        return None
    meta["size"] = info.st_size
    # Unchanged size, time and inode: the previous fingerprint stands.
    if previous and previous.get("_stamp") == meta["_stamp"] and "fp" in previous:
        meta["fp"] = previous["fp"]
    else:
        fingerprint = _fingerprint(path, key)
        if fingerprint is None:
            meta["unreadable"] = True
        else:
            meta["fp"] = fingerprint
    return meta


def _public(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    return None if meta is None else {k: v for k, v in meta.items() if not k.startswith("_")}


def file_events(
    paths: list[str], key: bytes, previous: dict[str, dict[str, Any]], host: str, at: str
) -> tuple[dict[str, dict[str, Any]], list[Event]]:
    current: dict[str, dict[str, Any]] = {}
    for path in paths:
        meta = describe(path, key, previous.get(path))
        if meta is not None:
            current[path] = meta
    events = []
    for path in sorted(set(previous) | set(current)):
        before, after = _public(previous.get(path)), _public(current.get(path))
        if before == after:
            continue
        action = "added" if before is None else "removed" if after is None else "modified"
        events.append({"at": at, "host": host, "kind": "file", "action": action, "path": path,
                       "before": before, "after": after})
    return current, events


# -- units ---------------------------------------------------------------------

Runner = Callable[[list[str]], str]


def _systemctl(args: list[str]) -> str:
    done = subprocess.run(args, capture_output=True, text=True, timeout=60, check=False)
    if done.returncode != 0:
        raise OSError(done.stderr.strip() or f"{args[0]} failed")
    return done.stdout


def unit_states(run: Runner = _systemctl) -> dict[str, str]:
    output = run(["systemctl", "list-unit-files", f"--type={UNIT_TYPES}", "--no-legend", "--no-pager", "--plain"])
    states = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            states[parts[0]] = parts[1]
    return states


def unit_events(current: dict[str, str], previous: dict[str, str], host: str, at: str) -> list[Event]:
    return [
        {"at": at, "host": host, "kind": "unit", "unit": unit,
         "before": previous.get(unit), "after": current.get(unit)}
        for unit in sorted(set(previous) | set(current))
        if previous.get(unit) != current.get(unit)
    ]


# -- one run -------------------------------------------------------------------

def collect(
    host: str,
    output: Path,
    key: bytes,
    *,
    watch: Iterable[str] = DEFAULT_WATCH,
    globs: Iterable[str] = DEFAULT_GLOBS,
    ignore: Iterable[str] = DEFAULT_IGNORE,
    logs: Path = DEFAULT_LOGS,
    units: Runner = _systemctl,
    now: Callable[[], str] = _now,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    started = clock()
    at = now()
    output.mkdir(parents=True, exist_ok=True)
    owner = _owner_of(output)
    state = output / "state"
    ignore = list(ignore)
    first = not (state / "files.json").exists()

    cursors = _read_json(state / "logs.json", {"dpkg": {}, "apt": {}})
    events: list[Event] = []
    events += dpkg_events(logs, cursors.setdefault("dpkg", {}), host)
    events += apt_events(logs, cursors.setdefault("apt", {}), host)

    previous_files = _read_json(state / "files.json", {})
    files, changed_files = file_events(watched_paths(watch, globs, ignore), key, previous_files, host, at)

    problems = []
    previous_units = _read_json(state / "units.json", None)
    try:
        current_units = unit_states(units)
    except OSError as error:
        current_units = previous_units or {}
        problems.append(f"systemctl: {error}")

    if first:
        events.append({"at": at, "host": host, "kind": "baseline", "files": len(files),
                       "units": len(current_units), "unreadable": sum(1 for m in files.values() if m.get("unreadable"))})
    else:
        events += changed_files
        events += unit_events(current_units, previous_units or {}, host, at)

    if events:
        journal = output / "events.jsonl"
        with journal.open("a", encoding="utf-8") as stream:
            for event in events:
                stream.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
        _give(journal, owner)
    _write_json(state / "files.json", files, owner)
    _write_json(state / "units.json", current_units, owner)
    _write_json(state / "logs.json", cursors, owner)
    summary = {
        "host": host, "collector_version": COLLECTOR_VERSION, "last_run": at,
        "seconds": round(clock() - started, 1), "events": len(events),
        "files": len(files), "units": len(current_units), "problems": problems,
    }
    _write_json(output / "host.json", summary, owner)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aistack-host-collector", description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", required=True, help="the host's name in AIStack (gigabyte, raspberry)")
    parser.add_argument("--output", required=True, type=Path, help="its directory, owned by the account AIStack reads it as")
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)

    if not args.output.is_dir():
        print(f"{args.output} does not exist: create it first, owned by the account AIStack runs as", file=sys.stderr)
        return 2
    config = read_config(args.config)
    lock_path = args.output / "state" / "lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    _give(lock_path.parent, _owner_of(args.output))
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another run is at work", file=sys.stderr)
            return 0
        summary = collect(
            args.host, args.output, load_key(args.key),
            watch=[*DEFAULT_WATCH, *config["watch"]],
            globs=[*DEFAULT_GLOBS, *config["glob"]],
            ignore=[*DEFAULT_IGNORE, *config["ignore"]],
        )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
