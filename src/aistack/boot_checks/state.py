"""
The verdict of the start-up checks and the incidents since the start (ADR-0032, slice B2).

`boot-check.json` is the state this service keeps for itself, rewritten
whole at every pass: the overall status, how many anomalies, each control's
answer, and the incidents since the last start. An incident is a control
that failed after the start; when it passes again it is *resolved*, and it
stays in the list until the next start, so the detail page can say what
happened even though the indicator is green again. Names and counts only,
never a line of a log.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.boot_checks.controls import ANOMALIES, OK, PENDING, UNKNOWN, Result
from aistack.boot_checks.facts import BootFacts
from aistack.boot_checks import usage as usage_journal
from aistack.boot_checks.history import DEFAULT_RETENTION, Event, Retention, history_file, prune, read_history, seeds, transitions

STATE = "boot-check.json"
# A companion's verdict is a file of its own, named after the host in hosts.yml.
_HOST_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,40}$")


def state_file(host: str | None = None) -> str:
    """`boot-check.json` for this host, `boot-check-<host>.json` for a companion; a name that is not a plain one is refused."""

    if host is None:
        return STATE

    if not _HOST_NAME.match(host):
        raise ValueError(f"not a host name: {host!r}")

    return f"boot-check-{host}.json"
MAX_INCIDENTS = 200


@dataclass(frozen=True)
class Incident:
    control: str
    status: str
    first_seen: str
    summary: str
    resolved_at: str | None = None
    # What was recorded in the hours before it began (O8), as sentences, oldest first. `None` = not built yet,
    # `()` = built and nothing was recorded: the two are not the same, so a built one is never built again.
    before: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Explanation:
    """
    What the AI engine said of one anomaly (B5c): text only, never a verdict, never executed. It belongs to the
    control, its status and its sentence as they were when it was asked; an empty `text` marks a question that
    was asked and not answered, so it is not asked again at every pass. `by` names the engine that answered.
    """

    control: str
    status: str
    summary: str
    text: str
    by: str
    asked_at: str
    # What the explanation rests on besides the sentence (O9): how many log lines of which container, never the lines.
    basis: tuple[str, ...] = ()


@dataclass(frozen=True)
class Verdict:
    """The overall answer. `anomalies` counts the controls to watch or to fix."""

    overall: str
    anomalies: int
    checked_at: str
    boot_id: str
    booted_at: str | None
    results: tuple[Result, ...]
    incidents: tuple[Incident, ...] = field(default_factory=tuple)
    note: str = ""
    # B5a: the circumstances that held, and the extra controls they chose (a subset of the results).
    circumstances: tuple[str, ...] = ()
    extra: tuple[str, ...] = ()
    # B5b: who chose the extra controls ("rules" or "engine", empty before any choice) and the sentence the engine gave.
    chosen_by: str = ""
    choice_reason: str = ""
    # B5c: what the engine said of the anomalies, one entry per anomaly explained.
    explanations: tuple[Explanation, ...] = ()


def overall(results: list[Result]) -> str:
    """Critical over watch over pending over ok: the worst answer wins, pending is not an anomaly."""

    statuses = {result.status for result in results}

    for status in ("critical", "warning", PENDING):
        if status in statuses:
            return status

    return OK


def judge(
    results: list[Result],
    facts: BootFacts,
    now: datetime,
    previous: Verdict | None = None,
    circumstances: tuple[str, ...] = (),
    extra: tuple[str, ...] = (),
    chosen_by: str = "",
    choice_reason: str = "",
) -> Verdict:
    """The verdict of this pass, and the incidents carried over from the passes since the same start."""

    return replace(
        _judge(results, facts.boot_id, facts.booted_at, now, previous),
        circumstances=circumstances,
        extra=extra,
        chosen_by=chosen_by,
        choice_reason=choice_reason,
    )


def judge_silent(results: list[Result], now: datetime, previous: Verdict | None = None) -> Verdict:
    """The verdict of a machine that wrote no usable facts: its last start and its incidents are kept, the silence is added."""

    boot_id = previous.boot_id if previous is not None else ""
    booted = datetime.fromisoformat(previous.booted_at) if previous is not None and previous.booted_at else None

    return _judge(results, boot_id, booted, now, previous)


def _judge(results: list[Result], boot_id: str, booted_at: datetime | None, now: datetime, previous: Verdict | None) -> Verdict:
    stamp = now.isoformat(timespec="seconds")
    carried = previous.incidents if previous is not None and previous.boot_id == boot_id else ()
    incidents = {item.control: item for item in carried if item.resolved_at is None}
    kept = [item for item in carried if item.resolved_at is not None]

    for result in results:
        if result.status in ANOMALIES and result.control not in incidents:
            incidents[result.control] = Incident(result.control, result.status, stamp, result.summary)
        elif result.status not in ANOMALIES and result.control in incidents:
            opened = incidents.pop(result.control)
            kept.append(Incident(opened.control, opened.status, opened.first_seen, opened.summary, stamp, opened.before))

    return Verdict(
        overall=overall(results),
        anomalies=sum(1 for result in results if result.status in ANOMALIES),
        checked_at=stamp,
        boot_id=boot_id,
        booted_at=booted_at.isoformat(timespec="seconds") if booted_at else None,
        results=tuple(results),
        incidents=tuple([*kept, *incidents.values()][-MAX_INCIDENTS:]),
    )


def unknown(now: datetime, note: str) -> Verdict:
    """No facts to judge: the state says so, never a green."""

    return Verdict(UNKNOWN, 0, now.isoformat(timespec="seconds"), "", None, (), (), note)


def write_verdict(directory: Path, verdict: Verdict, host: str | None = None, keep: Retention = DEFAULT_RETENTION) -> None:
    """Write the state of this pass; what changed since the last one goes to the journal (O2), which never stops the state."""

    directory.mkdir(parents=True, exist_ok=True)
    previous = read_verdict(directory, host)

    with tempfile.NamedTemporaryFile("w", dir=directory, delete=False, encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(verdict), indent=1, sort_keys=True) + "\n")
        temporary = Path(handle.name)

    os.chmod(temporary, 0o644)
    os.replace(temporary, directory / state_file(host))

    try:
        changed = transitions(previous, verdict)
        heard = (*read_history(directory, host), *changed)
        write_history(directory, [*changed, *seeds(heard, verdict)], datetime.fromisoformat(verdict.checked_at), host, keep)
    except (OSError, ValueError):
        return


def write_history(directory: Path, new: list[Event], now: datetime, host: str | None = None, keep: Retention = DEFAULT_RETENTION) -> None:
    """Add lines to the journal and trim it, atomically; nothing to add writes nothing."""

    if not new:
        return

    kept = prune((*read_history(directory, host), *new), now, keep)

    with tempfile.NamedTemporaryFile("w", dir=directory, delete=False, encoding="utf-8") as handle:
        for event in kept:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")

        temporary = Path(handle.name)

    os.chmod(temporary, 0o644)
    os.replace(temporary, directory / history_file(host))


def _result(raw: Any) -> Result | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("control"), str):
        return None

    return Result(
        raw["control"],
        str(raw.get("status", UNKNOWN)),
        str(raw.get("summary", "")),
        tuple(str(item) for item in raw.get("details", ()) if isinstance(item, str)),
        str(raw.get("finding", "")),
    )


def _explanation(raw: Any) -> Explanation | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("control"), str):
        return None

    return Explanation(
        raw["control"],
        str(raw.get("status", "")),
        str(raw.get("summary", "")),
        str(raw.get("text", "")),
        str(raw.get("by", "")),
        str(raw.get("asked_at", "")),
        tuple(str(item) for item in raw["basis"]) if isinstance(raw.get("basis"), list) else (),
    )


def _incident(raw: Any) -> Incident | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("control"), str):
        return None

    return Incident(
        raw["control"],
        str(raw.get("status", "")),
        str(raw.get("first_seen", "")),
        str(raw.get("summary", "")),
        str(raw["resolved_at"]) if raw.get("resolved_at") else None,
        tuple(str(item) for item in raw["before"]) if isinstance(raw.get("before"), list) else None,
    )


def read_verdict(directory: Path, host: str | None = None) -> Verdict | None:
    """The last verdict; `None` when there is none or the file is not one (a damaged file is never a green)."""

    try:
        raw = json.loads((directory / state_file(host)).read_text(encoding="utf-8"))
        datetime.fromisoformat(str(raw["checked_at"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None

    if not isinstance(raw, dict):
        return None

    results = [item for item in (_result(entry) for entry in raw.get("results", ())) if item is not None]
    incidents = [item for item in (_incident(entry) for entry in raw.get("incidents", ())) if item is not None]

    return Verdict(
        overall=str(raw.get("overall", UNKNOWN)),
        anomalies=raw["anomalies"] if isinstance(raw.get("anomalies"), int) else 0,
        checked_at=str(raw["checked_at"]),
        boot_id=str(raw.get("boot_id", "")),
        booted_at=str(raw["booted_at"]) if raw.get("booted_at") else None,
        results=tuple(results),
        incidents=tuple(incidents),
        note=str(raw.get("note", "")),
        circumstances=tuple(str(item) for item in raw.get("circumstances", ()) if isinstance(item, str)),
        extra=tuple(str(item) for item in raw.get("extra", ()) if isinstance(item, str)),
        chosen_by=str(raw.get("chosen_by", "")),
        choice_reason=str(raw.get("choice_reason", "")),
        explanations=tuple(item for item in (_explanation(entry) for entry in raw.get("explanations", ())) if item is not None),
    )


def age_seconds(verdict: Verdict, now: datetime | None = None) -> float:
    """How old the verdict is, so a reader can refuse a stale green."""

    checked = datetime.fromisoformat(verdict.checked_at)
    checked = checked if checked.tzinfo else checked.replace(tzinfo=timezone.utc)

    return ((now or datetime.now(timezone.utc)) - checked).total_seconds()


def write_usage(directory: Path, current: tuple[usage_journal.Sample, ...], now: datetime, days: int) -> list[usage_journal.Sample]:
    """
    Keep a sample of each data disk about every 7 hours (O4b) and return the journal as it stands; a disk that
    has a recent sample adds nothing and nothing to add writes nothing. A journal that cannot be written is the
    one that was read.
    """

    kept = usage_journal.read_history(directory)
    new = usage_journal.due(kept, current, now)

    if not new:
        return kept

    everything = usage_journal.prune([*kept, *new], now, days)

    try:
        directory.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", dir=directory, delete=False, encoding="utf-8") as handle:
            for sample in everything:
                line = {"at": sample.at.isoformat(timespec="seconds"), "point": sample.point, "total": sample.total, "used": sample.used}
                handle.write(json.dumps(line, sort_keys=True) + "\n")

            temporary = Path(handle.name)

        os.chmod(temporary, 0o644)
        os.replace(temporary, directory / usage_journal.USAGE)
    except OSError:
        return kept

    return everything
