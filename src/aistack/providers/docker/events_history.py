from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history

# A dedicated root, not `reports/generated/`'s own flat `history/` —
# on purpose, mirroring `aistack.timemachine.projection.explications`'
# own reasoning for keeping Explications under `generated_dir /
# "explications"`: `aistack.timemachine.projection
# .project_observation_history` walks every stem
# `available_stems(generated_dir)` finds and would otherwise try its
# own generic `version`/`provenance` envelope parse against this
# stream's real shape (a `since`/`until`/`events` batch, not a single
# subject's own snapshot) and either silently see nothing worth adding
# beyond the baseline, or — worse — misread it. A dedicated projector,
# `aistack.timemachine.projection.docker_events.project_docker_events`,
# is what actually understands this shape; keeping it off the generic
# walk's own root is what keeps the two from double-projecting the
# same batch under two different fact models.
DEFAULT_OUTPUT_PATH = Path("reports/generated/docker-events/docker-events.json")


def record_docker_events(
    events: list[dict[str, Any]],
    *,
    since: str,
    until: str,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path | None:
    """
    Persist one poll cycle's newly observed Docker events to history —
    `aistack.priority.decision_history.record_decision`'s own "write
    on change, not every poll" cadence, applied here: a monitor polling
    every `aistack.cli.docker_events_monitor.POLL_SECONDS` would
    otherwise write an near-empty batch every cycle, most of which
    observe nothing new.

    `events` is expected already enriched
    (`aistack.providers.docker.events.enrich`) — `subject`/
    `occurred_at`/`action` computed once, by the collector that has
    the raw payload in hand, not re-derived here or by the projector
    that reads this file back (`aistack.timemachine.projection
    .project_observation_history`'s own docstring: "already present in
    the data, not derived here" — the same rule, applied to this
    stream's own writer).

    Returns `None`, writing nothing, when `events` is empty — the same
    convention `record_decision` already holds for "nothing to say this
    cycle."

    **No `collected_at` field in the content.** `decision_history
    .serialize_decision`'s own docstring names the reason this module
    follows too: the history filename `write_artifact_with_history`
    stamps already states the recording instant; a second field
    inside the content would only be able to repeat or drift from it.
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
