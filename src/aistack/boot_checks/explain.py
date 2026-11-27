"""
The AI engine's words on the anomalies of a start (ADR-0032 § 3, slice B5c).

For each control to watch or to fix, an engine of the house may say in plain French what it means and
what to look at. It is text, shown on the page under the mention "the AI's explanation, not verified",
and nothing more: it never changes a verdict, never reaches the morning message, is never executed, and
a control that passes again loses its explanation. The matter it is given is the control, its sentence
and the names the control carries, cleaned and cut; the caller `boot_checks` is internal, so nothing
leaves your machines.

An anomaly is explained once: the explanation stands as long as the control keeps the same status and
the same sentence during the same start, so a pass every fifteen minutes does not ask again. A question
that got no answer is kept as such and tried again after `RETRY_MINUTES`, never at every pass.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone

from aistack.boot_checks.choice import Ask, Matter
from aistack.boot_checks.controls import ANOMALIES, Result
from aistack.boot_checks.excerpts import Excerpt, basis, block
from aistack.boot_checks.state import Explanation, Verdict
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer

# At most this many anomalies are explained at one pass, in the order of the verdict.
MAX_EXPLAINED = 3
RETRY_MINUTES = 60
TEXT_LIMIT = 900
NAMES_SHOWN = 8
LANGUAGE = "fr"

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]+")
# What a small engine adds that AIStack cannot honour: a greeting, a question to the reader, a promise to follow up.
_GREETING = re.compile(r"^\W*(salut|bonjour|bonsoir|coucou|hello|hi|hey)\b(\W+\w+){0,2}\W*$", re.IGNORECASE)
_SOLICITATION = re.compile(r"\?\W*$|fais[- ]moi savoir|dis[- ]moi|tiens[- ]moi au courant|n'h[ée]site pas|let me know", re.IGNORECASE)
# Said to the engine after the facts, in the last words it reads: a small model follows these better there.
RULES = (
    "Rules for your answer: do not greet the reader. Do not ask the reader a question and do not promise to follow up: "
    "AIStack cannot receive a reply. Use only the facts above and the log lines given: never add a cause, a number or a "
    "name that is not there, and say so when you do not know. At most two short paragraphs: what it means, then what to look at."
)


def _line(text: str, limit: int) -> str:
    return " ".join(_CONTROL_CHARACTERS.sub(" ", text).split())[:limit]


def clean(text: str) -> str:
    """The engine's words as the page may show them: no control character, paragraphs kept, cut at `TEXT_LIMIT`."""

    paragraphs = [" ".join(_CONTROL_CHARACTERS.sub(" ", part).split()) for part in text.replace("\r", "").split("\n")]
    kept = [part for part in paragraphs if part]

    if kept and _GREETING.match(kept[0]):
        kept = kept[1:]

    while kept and len(kept[-1]) < 120 and _SOLICITATION.search(kept[-1]):
        kept = kept[:-1]

    return "\n".join(kept)[:TEXT_LIMIT].strip()


def matter_of(result: Result) -> Matter:
    """What the engine is asked about: the control, its sentence and a few of the names it carries."""

    names = ", ".join(_line(name, 60) for name in result.details[:NAMES_SHOWN]) or "none"
    body = f"{_line(result.summary, 200)} (status: {_line(result.status, 20)}; names: {names})"

    return Matter(_line(result.control, 40), _line(result.finding or result.control, 40), body)


def context_of(found: tuple[str, ...], results: list[Result]) -> str:
    """The circumstances and what the other controls said, in a few lines: the engine reads an anomaly in its setting."""

    lines = [f"circumstances of this start: {', '.join(found) or 'none'}"]
    lines.extend(f"{_line(item.control, 40)}: {_line(item.status, 20)}, {_line(item.summary, 120)}" for item in results[:20])

    return "\n".join(lines)


def standing(
    results: list[Result], previous: Verdict | None, boot_id: str, now: datetime
) -> tuple[tuple[Explanation, ...], tuple[Result, ...]]:
    """What already stands, and the anomalies still to explain (at most `MAX_EXPLAINED` in all)."""

    anomalies = [item for item in results if item.status in ANOMALIES][:MAX_EXPLAINED]
    known = {item.control: item for item in previous.explanations} if previous is not None and previous.boot_id == boot_id else {}
    kept: list[Explanation] = []
    todo: list[Result] = []

    for anomaly in anomalies:
        old = known.get(anomaly.control)
        same = old is not None and (old.status, old.summary) == (anomaly.status, anomaly.summary)
        fresh = old is not None and _age(old, now) < RETRY_MINUTES * 60

        if old is not None and same and (old.text or fresh):
            kept.append(old)
        else:
            todo.append(anomaly)

    return tuple(kept), tuple(todo)


def _age(item: Explanation, now: datetime) -> float:
    try:
        asked = datetime.fromisoformat(item.asked_at)
    except ValueError:
        return float("inf")

    asked = asked if asked.tzinfo else asked.replace(tzinfo=timezone.utc)

    return (now - asked).total_seconds()


def markers(todo: tuple[Result, ...], now: datetime) -> tuple[Explanation, ...]:
    """Questions about to be asked, written first: a pass cut short leaves them, and nothing is asked again at once."""

    stamp = now.isoformat(timespec="seconds")

    return tuple(Explanation(item.control, item.status, item.summary, "", "", stamp) for item in todo)


def _within(ask: Ask, matter: Matter, context: str, seconds: float) -> AIRuntimeAnswer | None:
    box: list[AIRuntimeAnswer] = []

    def run() -> None:
        try:
            box.append(ask(matter, "explain", LANGUAGE, context))
        except Exception:  # an engine may fail in many ways; the anomaly stays unexplained
            return

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(max(seconds, 0.0))

    return box[0] if box else None


def _excerpts(find: Callable[[Result], tuple[Excerpt, ...]] | None, item: Result) -> tuple[Excerpt, ...]:
    if find is None:
        return ()

    try:
        return find(item)
    except Exception:  # a log that cannot be read adds nothing: the anomaly is explained without it
        return ()


def explain(
    todo: tuple[Result, ...],
    found: tuple[str, ...],
    results: list[Result],
    ask: Ask,
    now: datetime,
    seconds: float,
    clock: Callable[[], float] = time.monotonic,
    excerpts: Callable[[Result], tuple[Excerpt, ...]] | None = None,
) -> tuple[Explanation, ...]:
    """One explanation per anomaly asked, within `seconds` for all of them; one that does not come stays a marker."""

    deadline = clock() + seconds
    context = context_of(found, results)
    stamp = now.isoformat(timespec="seconds")
    said: list[Explanation] = []

    for item in todo:
        lines = _excerpts(excerpts, item)
        left = deadline - clock()
        asked = "\n".join(part for part in (context, block(lines), RULES) if part)
        answer = _within(ask, matter_of(item), asked, left) if left > 0 else None
        text = clean(answer.response) if answer is not None and answer.reachable else ""
        said.append(
            Explanation(item.control, item.status, item.summary, text, answer.model[:80] if text and answer is not None else "", stamp, basis(lines) if text else ())
        )

    return tuple(said)


def wants_explaining(results: list[Result], previous: Verdict | None, boot_id: str, now: datetime) -> bool:
    return bool(standing(results, previous, boot_id, now)[1])

