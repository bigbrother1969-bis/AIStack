from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history
from aistack.history import latest_observations

# A dedicated directory, outside the stems `project_observation_history`
# walks: these batches are read only by
# `aistack.timemachine.projection.docker_events`, and the generic walk
# would misread them.
DEFAULT_OUTPUT_PATH = Path("reports/generated/docker-events/docker-events.json")


def record_docker_events(
    events: list[dict[str, Any]],
    *,
    since: str,
    until: str,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path | None:
    """Persist one poll cycle's new Docker events to history.

    `events` must already be enriched (`aistack.providers.docker.events
    .enrich`). Returns `None` and writes nothing when `events` is empty.
    The content has no `collected_at`: the history filename already
    records the instant.
    """

    if not events:
        return None

    content = (
        json.dumps(
            {"since": since, "until": until, "events": events},
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    latest_path, _ = write_artifact_with_history(content, output_path)

    return latest_path


def read_recent_docker_events(
    since: datetime,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> list[dict[str, Any]]:
    """Every recorded event in batches written at or after `since`
    (read by `aistack.runtime.restart_loop`).

    An unreadable batch is skipped so one bad file cannot break a health
    page.
    """

    stem = output_path.stem
    events: list[dict[str, Any]] = []
    for observation in latest_observations(output_path.parent, stem):
        if observation.observed_at < since:
            continue
        try:
            payload = json.loads(observation.read())
        except (OSError, ValueError):
            continue
        batch = payload.get("events") if isinstance(payload, dict) else None
        if isinstance(batch, list):
            events.extend(event for event in batch if isinstance(event, dict))
    return events
