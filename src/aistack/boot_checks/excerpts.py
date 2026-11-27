"""
Lines of a container's log, kept for the AI engine's explanation of an anomaly (ADR-0032, slice O9).

The code judges; the engine only explains. Explaining "six databases recovered" is better done with the few lines the
database itself wrote about its recovery than with the sentence alone. For the controls that name a container (the
databases that recovered, a container that is unhealthy), a few lines of that container's log since the start are read,
the relevant ones kept, cleaned, and handed to the engine with the question. The caller `boot_checks` is internal, so
the lines never leave your machines.

They are used for that one question and then dropped: the verdict, the history and the page keep only how many lines of
which container the explanation rests on, never the lines. What is cleaned away: passwords, tokens, keys, credentials
in an address, e-mail addresses, IP addresses, long opaque strings and control characters; every line is cut. A log that
cannot be read adds nothing and the anomaly is explained without it.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from aistack.boot_checks.controls import Result

CONTROLS = ("database_recovery", "container_health")
MAX_CONTAINERS = 3
MAX_LINES = 6
LINE_LIMIT = 200
READ_TAIL = 400
TIMEOUT_SECONDS = 10

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]+")
_RELEVANT = re.compile(
    r"recover|not properly shut|shut ?down|redo|interrupt|invalid record|corrupt|fatal|panic|error|abort|crash|"
    r"terminat|killed|out of memory|oom|fail|unhealthy|ready to accept|permission denied",
    re.IGNORECASE,
)
_MASKS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"://[^/\s:@]+:[^@\s]+@"), "://***@"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|authorization|bearer)\b(\s*[=:]\s*|\s+)\S+"), r"\1=***"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<email>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<ip>"),
    (re.compile(r"[A-Za-z0-9+/_=-]{32,}"), "<opaque>"),
)

Run = Callable[[list[str]], str | None]


@dataclass(frozen=True)
class Excerpt:
    """The lines kept of one container's log, and how many were read to find them."""

    name: str
    lines: tuple[str, ...]
    read: int


def clean_line(text: str) -> str:
    """One log line as the engine may see it: no control character, secrets and addresses masked, cut."""

    line = " ".join(_CONTROL_CHARACTERS.sub(" ", text).split())

    for pattern, mask in _MASKS:
        line = pattern.sub(mask, line)

    return line[:LINE_LIMIT]


def choose(lines: list[str], limit: int = MAX_LINES) -> tuple[str, ...]:
    """The last `limit` relevant lines, cleaned, a line repeated one after the other said once."""

    kept: list[str] = []

    for line in lines:
        cleaned = clean_line(line)

        if cleaned and _RELEVANT.search(cleaned) and (not kept or kept[-1] != cleaned):
            kept.append(cleaned)

    return tuple(kept[-limit:])


def _docker(command: list[str]) -> str | None:
    try:
        done = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=TIMEOUT_SECONDS, check=False, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None

    # A database writes its log on the error stream: both are read.
    return (done.stdout + done.stderr) if done.returncode == 0 else None


def read_container(name: str, since: datetime | None, run: Run = _docker) -> Excerpt | None:
    """What is kept of the log of `name` since `since`; `None` when the name is not a container name or the log cannot be read."""

    if not _NAME.match(name):
        return None

    command = ["docker", "logs", "--tail", str(READ_TAIL)]

    if since is not None:
        command += ["--since", since.isoformat()]

    raw = run([*command, name])

    if raw is None:
        return None

    lines = raw.splitlines()

    return Excerpt(name, choose(lines), len(lines))


def excerpts_for(result: Result, since: datetime | None, run: Run = _docker) -> tuple[Excerpt, ...]:
    """The excerpts of the containers an anomaly names; none for a control that does not name a container."""

    if result.control not in CONTROLS:
        return ()

    found = (read_container(name, since, run) for name in result.details[:MAX_CONTAINERS])

    return tuple(item for item in found if item is not None and item.lines)


def block(excerpts: tuple[Excerpt, ...]) -> str:
    """The lines as the engine is given them, each container under its name."""

    parts = [f"log lines of {item.name} (cleaned, {len(item.lines)} of {item.read} read):\n" + "\n".join(f"- {line}" for line in item.lines) for item in excerpts]

    return "\n".join(parts)


def basis(excerpts: tuple[Excerpt, ...]) -> tuple[str, ...]:
    """What the explanation rests on, without the lines: how many of which container."""

    return tuple(f"{len(item.lines)} log line(s) of {item.name} kept ({item.read} read)" for item in excerpts)
