"""
`hosts.yml` and the records the host collectors write (`ADR-0020`):
`<directory>/host.json` (the last run) and `<directory>/events.jsonl`
(one event per line, appended, never rewritten — a line's number is
its identity).

Read-only. A directory that cannot be read (the Raspberry's disk not
mounted) is said, never taken for a host with nothing to tell.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from aistack.config import configured

SHIPPED = Path(__file__).resolve().parent / "definitions" / "hosts.yml"


@dataclass(frozen=True)
class TracedHost:
    name: str
    directory: Path


@dataclass(frozen=True)
class HostsDeclaration:
    hosts: tuple[TracedHost, ...]
    silent_after: timedelta


def load_hosts_declaration(generated_dir: Path, path: Path | None = None) -> HostsDeclaration:
    source = path if path is not None else configured(SHIPPED)
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{source}: not a mapping")
    hosts = []
    for name, raw in (data.get("hosts") or {}).items():
        if not isinstance(raw, dict) or not raw.get("directory"):
            raise ValueError(f"{source}: host `{name}` names no `directory`")
        directory = Path(str(raw["directory"]))
        hosts.append(TracedHost(str(name), directory if directory.is_absolute() else generated_dir / directory))
    return HostsDeclaration(tuple(hosts), timedelta(minutes=float(data.get("silent_after_minutes", 60))))


@dataclass
class HostRecords:
    host: str
    directory: Path
    summary: dict[str, Any] | None = None
    # (line number from 1, event), in the order written.
    events: list[tuple[int, dict[str, Any]]] = field(default_factory=list)
    problem: str = ""

    @property
    def last_run(self) -> datetime | None:
        value = (self.summary or {}).get("last_run")
        try:
            return datetime.fromisoformat(str(value)) if value else None
        except ValueError:
            return None

    def silent(self, now: datetime, after: timedelta) -> bool:
        last = self.last_run
        return last is None or now - last > after


def read_host(host: TracedHost) -> HostRecords:
    records = HostRecords(host.name, host.directory)
    try:
        records.summary = json.loads((host.directory / "host.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        records.problem = f"no record in {host.directory} (collector not installed, or its disk not mounted)"
        return records
    except (OSError, ValueError) as error:
        records.problem = f"{host.directory}: {error}"
        return records
    try:
        with (host.directory / "events.jsonl").open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, start=1):
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("at"):
                    records.events.append((number, event))
    except FileNotFoundError:
        pass
    except OSError as error:
        records.problem = f"{host.directory}/events.jsonl: {error}"
    return records


def read_all(declaration: HostsDeclaration) -> list[HostRecords]:
    return [read_host(host) for host in declaration.hosts]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
