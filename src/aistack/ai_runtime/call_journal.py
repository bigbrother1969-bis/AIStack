"""
The journal of AI calls (`ADR-0029` § 6): one line per question asked to a
model, saying who asked, which engine answered, how long it took and what
was set aside. Never the question, the answer or the evidence: a line names
the caller, the operation and the engine, nothing the engine was given.

It is the state the console keeps for itself, written by the process that
asked, and it never stops a question: a full or read-only disk loses a
line, not an answer.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer

JOURNAL_FILE = "ai-calls.jsonl"
DEFAULT_JOURNAL_DIR = Path("reports/generated/ai-calls")
# Lines older than this are dropped when the journal is trimmed (`ADR-0029` open point, proposed value).
KEPT_DAYS = 90
# The journal is trimmed once it passes TRIM_AT lines, whatever their age.
TRIM_AT = 20000
REASON_LIMIT = 300

# Who asks (`ADR-0029` open point: the list is read with the owner).
TROUBLESHOOTING = "troubleshooting"
SECURITY_PAGE = "security.page"
VIGIL_REASON = "vigil.reason"
AI_COMPARE = "ai.compare"


@dataclass(frozen=True)
class Call:
    at: str
    caller: str
    operation: str
    language: str
    answered_by: str
    reached_external: bool
    reachable: bool
    seconds: float
    set_aside: str = ""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def call_of(caller: str, answer: AIRuntimeAnswer, seconds: float, at: str | None = None) -> Call:
    """One line from one answer: what it names (engine, reasons), never what it holds (prompt, response)."""

    return Call(
        at=at or now_iso(),
        caller=caller,
        operation=answer.operation,
        language=answer.language,
        answered_by=answer.model,
        reached_external=answer.external,
        reachable=answer.reachable,
        seconds=round(seconds, 2),
        set_aside=answer.unreachable_reason[:REASON_LIMIT],
    )


def append(directory: Path, call: Call, today: datetime | None = None) -> None:
    """One call, one line; never raises (the question must go on)."""

    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / JOURNAL_FILE
        line = json.dumps(
            {
                "at": call.at,
                "caller": call.caller,
                "operation": call.operation,
                "language": call.language,
                "answered_by": call.answered_by,
                "reached_external": call.reached_external,
                "reachable": call.reachable,
                "seconds": call.seconds,
                "set_aside": call.set_aside,
            },
            ensure_ascii=False,
        )

        with path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")

        lines = path.read_text(encoding="utf-8").splitlines()

        if len(lines) > TRIM_AT:
            path.write_text("\n".join(_recent(lines, today or datetime.now(timezone.utc))) + "\n", encoding="utf-8")
    except OSError:
        pass


def _recent(lines: list[str], today: datetime) -> list[str]:
    """The lines newer than KEPT_DAYS; a line with no readable date is kept, so nothing is lost by guessing."""

    limit = today - timedelta(days=KEPT_DAYS)
    kept: list[str] = []

    for line in lines:
        try:
            when = datetime.fromisoformat(json.loads(line)["at"])
        except (ValueError, KeyError, TypeError):
            kept.append(line)
            continue

        if when >= limit:
            kept.append(line)

    return kept[-TRIM_AT:]


def read(directory: Path, limit: int = 100) -> tuple[Call, ...]:
    """The newest `limit` calls, newest first; unreadable lines are skipped."""

    try:
        lines = (directory / JOURNAL_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()

    found: list[Call] = []

    for line in reversed(lines):
        try:
            data = json.loads(line)
            found.append(
                Call(
                    at=str(data["at"]),
                    caller=str(data["caller"]),
                    operation=str(data["operation"]),
                    language=str(data["language"]),
                    answered_by=str(data["answered_by"]),
                    reached_external=bool(data["reached_external"]),
                    reachable=bool(data["reachable"]),
                    seconds=float(data["seconds"]),
                    set_aside=str(data.get("set_aside") or ""),
                )
            )
        except (ValueError, KeyError, TypeError):
            continue

        if len(found) >= limit:
            break

    return tuple(found)


def journaled(
    ask: Callable[..., AIRuntimeAnswer], caller: str, directory: Path = DEFAULT_JOURNAL_DIR
) -> Callable[..., AIRuntimeAnswer]:
    """
    `ask`, with each call written to the journal under `caller`. The answer
    is returned as it is: the journal watches the call, it does not change
    its route.
    """

    def asked(*args: Any, **kwargs: Any) -> AIRuntimeAnswer:
        started = time.monotonic()
        answer = ask(*args, **kwargs)
        append(directory, call_of(caller, answer, time.monotonic() - started))
        return answer

    return asked
