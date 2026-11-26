"""
Who chooses the extra controls of a start (ADR-0032 § 3, slice B5b).

The rules of B5a give a floor: the controls the circumstances call for. An AI engine of the
house may add others from the same closed catalogue, up to `ai.max_extra_controls` in all, and
says why in one sentence. It can never take a control away: the one the rules call for stays,
so an engine that is silent, slow or wrong hides nothing. Whatever it says is validated here:
an identifier outside the catalogue is dropped, a sentence is cleaned and cut, an answer that is
not the expected object counts as silence and the rules decide.

The engine is asked once for a start and the circumstances it saw; the choice is kept in the
verdict and reused at the next passes. A choice made by the rules because the engine was silent
is tried again after `RETRY_MINUTES`, not at every pass. The verdict of each control is still
computed by code (`aistack.boot_checks.catalogue`), never by the engine.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from aistack.boot_checks.catalogue import choose
from aistack.boot_checks.controls import Result
from aistack.boot_checks.definition import EXTRA_CONTROLS, BootChecksDefinition
from aistack.boot_checks.state import Verdict, age_seconds
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer

RULES = "rules"
ENGINE = "engine"
# The language the engine writes its sentence in: the reference language, shown as it was written.
LANGUAGE = "fr"
RETRY_MINUTES = 60
# The vigil stops one pass at 300 s: the engine gets less, and the verdict of the rules is already written.
ASK_SECONDS = 240
REASON_LIMIT = 200
LINE_LIMIT = 160
MAX_LINES = 40

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]+")
_OBJECT = re.compile(r"\{.*?\}", re.DOTALL)

# What each control of the catalogue reads, in the words the engine is given.
READS = {
    "database_recovery": "counts the recoveries in the logs of the declared database containers since the start",
    "kernel_disk_errors": "counts the disk and file-system error lines in the kernel log since the start",
    "restart_cause": "tells why the previous run stopped (power cut, a shutdown that was asked for, unknown)",
    "backup_after_restart": "reads the backup domain when the start fell inside the backup window",
    "memory": "reads the memory pressure and the swap in use",
}

# (the matter, the language) -> the engine's answer; the call is `ask(matter, "choose", language)`.
Ask = Callable[..., AIRuntimeAnswer]


@dataclass(frozen=True)
class Choice:
    """The extra controls of this start, who chose them, and the sentence the engine gave."""

    controls: tuple[str, ...]
    by: str
    reason: str = ""


@dataclass(frozen=True)
class Matter:
    """What the engine is asked about: read-only, as `AIMatter` says."""

    subject: str
    signature: str
    interpretation: str
    remediation: str = ""
    confidence: str = "established"
    qualifications: tuple[str, ...] = ()


def _clean(text: str, limit: int) -> str:
    return " ".join(_CONTROL_CHARACTERS.sub(" ", text).split())[:limit]


def matter_of(found: tuple[str, ...], results: list[Result], definition: BootChecksDefinition, floor: tuple[str, ...]) -> Matter:
    """The circumstances, the base results (names of controls, statuses, counts) and the catalogue; no log line, no name of the host."""

    lines = [f"Circumstances computed by AIStack: {', '.join(found)}."]
    lines.append("Results of the base controls (control: status, sentence):")
    lines.extend(f"- {_clean(result.control, 40)}: {_clean(result.status, 20)}, {_clean(result.summary, LINE_LIMIT)}" for result in results[:MAX_LINES])
    lines.append("Catalogue of extra read-only controls (identifier: what it reads; circumstances that usually call for it):")
    lines.extend(
        f"- {name}: {READS[name]}; {', '.join(definition.catalogue.get(name, ())) or 'none declared'}" for name in EXTRA_CONTROLS
    )
    lines.append(
        f"AIStack runs in any case: {', '.join(floor) or 'none'}. You may add others; the limit is "
        f"{definition.ai_max_extra_controls} controls in all."
    )

    return Matter("start-up checks", ",".join(found), "\n".join(lines))


def parse(text: str, definition: BootChecksDefinition) -> tuple[tuple[str, ...], str] | None:
    """The identifiers of the catalogue and the sentence of an answer; `None` when it is not the object that was asked for."""

    for candidate in _OBJECT.findall(text or ""):
        try:
            data = json.loads(candidate)
        except ValueError:
            continue

        if not isinstance(data, dict) or not isinstance(data.get("controls"), list):
            continue

        wanted = [item for item in data["controls"] if isinstance(item, str)]
        known = tuple(dict.fromkeys(item for item in wanted if item in EXTRA_CONTROLS))
        reason = data.get("reason")

        return known, _clean(reason, REASON_LIMIT) if isinstance(reason, str) else ""

    return None


def _within(ask: Ask, matter: Matter, seconds: float) -> AIRuntimeAnswer | None:
    """The answer, or `None` when it does not come in time (the thread is left to die with the process)."""

    box: list[AIRuntimeAnswer] = []

    def run() -> None:
        try:
            box.append(ask(matter, "choose", LANGUAGE))
        except Exception:  # an engine may fail in many ways; the rules decide
            return

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(seconds)

    return box[0] if box else None


def reused(previous: Verdict | None, boot_id: str, found: tuple[str, ...], now: datetime) -> Choice | None:
    """The choice already made for this start and these circumstances, when it still stands."""

    if previous is None or not previous.chosen_by or previous.boot_id != boot_id or previous.circumstances != found:
        return None

    if previous.chosen_by == RULES and age_seconds(previous, now) >= RETRY_MINUTES * 60:
        return None

    return Choice(previous.extra, previous.chosen_by, previous.choice_reason)


def wants_engine(found: tuple[str, ...], definition: BootChecksDefinition, ask: Ask | None, previous: Verdict | None, boot_id: str, now: datetime) -> bool:
    """Whether the engine is to be asked at this pass: something to choose, an engine to ask, no choice standing."""

    return bool(found) and definition.ai_enabled and ask is not None and reused(previous, boot_id, found, now) is None


def decide(
    found: tuple[str, ...],
    results: list[Result],
    definition: BootChecksDefinition,
    ask: Ask | None,
    previous: Verdict | None,
    boot_id: str,
    now: datetime | None = None,
    seconds: float = ASK_SECONDS,
) -> Choice:
    """The extra controls of this start: the rules' floor, plus what a reachable engine adds from the catalogue."""

    now = now or datetime.now(timezone.utc)
    floor = choose(found, definition)

    if not found or not definition.ai_enabled or ask is None:
        return Choice(floor, RULES)

    standing = reused(previous, boot_id, found, now)

    if standing is not None:
        return standing

    answer = _within(ask, matter_of(found, results, definition, floor), seconds)
    chosen = parse(answer.response, definition) if answer is not None and answer.reachable else None

    if chosen is None:
        return Choice(floor, RULES)

    room = max(definition.ai_max_extra_controls - len(floor), 0)
    added = [name for name in chosen[0] if name not in floor][:room]
    wanted = {*floor, *added}

    return Choice(tuple(name for name in EXTRA_CONTROLS if name in wanted), ENGINE, chosen[1])

