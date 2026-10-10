"""
Restart loops counted from the docker-events history, complementing the
instantaneous check of `find_container_distress`.
"""

from __future__ import annotations

from aistack.contracts.finding_message import FindingMessage, part

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aistack.contracts.restart_loop import RestartLoop
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED
from aistack.providers.docker.events_history import (
    DEFAULT_OUTPUT_PATH,
    read_recent_docker_events,
)
from aistack.runtime.evaluate_services import (
    DOCKER_PROVIDER,
    SERVICE_DISTRESS_QUALIFICATIONS,
    SIGNATURE,
)

# An estimate: a loop seen in practice reached hundreds of deaths an hour,
# while a normal update or a manual restart dies once or twice.
RESTART_LOOP_WINDOW_MINUTES = 60
RESTART_LOOP_THRESHOLD = 5


def find_restart_loops(
    events: Iterable[Mapping[str, Any]],
    now: datetime,
    *,
    window_minutes: int = RESTART_LOOP_WINDOW_MINUTES,
    threshold: int = RESTART_LOOP_THRESHOLD,
) -> tuple[RestartLoop, ...]:
    """
    Return every subject with at least `threshold` `die` events in the last
    `window_minutes` before `now`, sorted by subject. Events without a
    readable `occurred_at` are not counted.
    """

    since = now - timedelta(minutes=window_minutes)
    deaths: Counter[str] = Counter()
    for event in events:
        if event.get("action") != "die":
            continue
        try:
            occurred = datetime.fromisoformat(str(event.get("occurred_at")))
        except ValueError:
            continue
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        if since <= occurred <= now:
            deaths[str(event.get("subject") or "")] += 1

    return tuple(
        RestartLoop(
            container=subject,
            restarts=count,
            window_minutes=window_minutes,
            threshold=threshold,
        )
        for subject, count in sorted(deaths.items())
        if subject and count >= threshold
    )


def evaluate_restart_loops(loops: Iterable[RestartLoop]) -> tuple[RuntimeFinding, ...]:
    """
    One `RuntimeFinding` per loop, with the same signature and qualifications
    as the instantaneous Services check.
    """

    return tuple(
        RuntimeFinding(
            subject=loop.container,
            signature=SIGNATURE,
            interpretation=(
                f"{loop.container} died and restarted {loop.restarts} times in "
                f"the last {loop.window_minutes} minutes (threshold "
                f"{loop.threshold}) — a restart loop, the condition "
                f"OPS-0004's third reference incident names, even though "
                f"Docker may report it 'running' between two crashes."
            ),
            remediation=(
                f"Read `docker logs {loop.container.split('/')[-1]}` for the "
                f"error it dies on at startup and fix that cause (storage, "
                f"configuration, a dependency) rather than restarting it — its "
                f"restart policy is already restarting it."
            ),
            message=FindingMessage(
                interpretation=(
                    part(
                        "findings.restart_loop.interpretation",
                        container=loop.container,
                        restarts=loop.restarts,
                        window=loop.window_minutes,
                        threshold=loop.threshold,
                    ),
                ),
                remediation=(
                    part(
                        "findings.restart_loop.remediation",
                        name=loop.container.split("/")[-1],
                    ),
                ),
            ),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(CitedReading(provider=DOCKER_PROVIDER, reading=loop),),
            qualifications=SERVICE_DISTRESS_QUALIFICATIONS,
        )
        for loop in loops
    )


def restart_loop_findings(
    now: datetime | None = None,
    *,
    events_output_path: Path = DEFAULT_OUTPUT_PATH,
) -> tuple[RuntimeFinding, ...]:
    """
    Read the recent docker-events history and return restart-loop findings.
    Best-effort: a missing or unreadable history yields no findings, not an
    error.
    """

    when = now if now is not None else datetime.now(timezone.utc)
    events = read_recent_docker_events(
        when - timedelta(minutes=RESTART_LOOP_WINDOW_MINUTES),
        output_path=events_output_path,
    )
    return evaluate_restart_loops(find_restart_loops(events, when))
