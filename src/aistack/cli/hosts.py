"""
`python -m aistack.cli.hosts` — the traced hosts (`ADR-0020`): for each
host `hosts.yml` declares, when its collector last ran, how many events
it recorded and of which kinds, whether it is silent (no run for longer
than `silent_after_minutes`) and any problem it reported.

    python -m aistack.cli.hosts            every host
    python -m aistack.cli.hosts --last 10  … and its ten latest events

Exit 1 when a host is silent or unreadable.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from aistack.cli.sandbox import data_dir
from aistack.hosts.records import HostRecords, load_hosts_declaration, now_utc, read_all
from aistack.timemachine.projection.host_changes import describe_event


def report(records: HostRecords, now: datetime, silent_after: object, last: int) -> list[str]:
    lines = [f"{records.host} — {records.directory}"]
    if records.problem and not records.summary:
        lines.append(f"  ILLISIBLE : {records.problem}")
        return lines
    summary = records.summary or {}
    silent = records.silent(now, silent_after)  # type: ignore[arg-type]
    lines.append(
        f"  dernier passage : {summary.get('last_run', '?')} ({summary.get('seconds', '?')} s)"
        + ("  — SILENCIEUX" if silent else "")
    )
    lines.append(f"  suivis : {summary.get('files', '?')} fichiers, {summary.get('units', '?')} unités")
    kinds = Counter(str(event.get("kind")) for _, event in records.events)
    lines.append("  événements : " + (", ".join(f"{kind} {count}" for kind, count in sorted(kinds.items())) or "aucun"))
    for problem in summary.get("problems") or []:
        lines.append(f"  problème : {problem}")
    if records.problem:
        lines.append(f"  problème : {records.problem}")
    for _, event in records.events[-last:] if last else []:
        subject, action, detail = describe_event(records.host, event)
        lines.append(f"    {event['at']}  {event.get('kind')}  {action}  {subject}{'  ' + detail if detail else ''}")
    return lines


def main(argv: list[str] | None = None, root: Path | None = None, now: datetime | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aistack.cli.hosts", description=__doc__.split("\n\n")[0])
    parser.add_argument("--last", type=int, default=0, help="also show each host's N latest events")
    args = parser.parse_args(argv)

    declaration = load_hosts_declaration(data_dir(root or Path.cwd()))
    moment = now or now_utc()
    healthy = True
    for records in read_all(declaration):
        print("\n".join(report(records, moment, declaration.silent_after, args.last)))
        if (records.problem and not records.summary) or records.silent(moment, declaration.silent_after):
            healthy = False
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
