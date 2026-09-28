from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from aistack.generators.history import write_artifact_with_history

# A dedicated root per stream, `generated_dir / "collection-gaps" /
# <stream_stem>` — the same reasoning `aistack.providers.docker
# .events_history`'s own `DEFAULT_OUTPUT_PATH` already gives for
# staying off `generated_dir`'s own flat `history/` directory: the
# generic walk's `available_stems(generated_dir)` never finds it, so a
# stream's ordinary observations and its collection-gap facts are
# never mixed under the same stem.
DEFAULT_COLLECTION_GAPS_ROOT = Path("reports/generated") / "collection-gaps"


def record_collection_gap(
    stream_stem: str,
    *,
    checkpoint_until: str | None,
    now: datetime,
    generated_dir: Path = Path("reports/generated"),
) -> Path | None:
    """
    `ADR-0011` § 9 ("collection gaps are their own fact", R11) — the
    shared mechanism every 1.5 monitor calls once at its own startup,
    decided with the owner 2026-09-28 to build before stacking three
    more polling monitors on the same gap `docker_events_monitor`
    already has (`aistack.cli.docker_events_monitor.load_checkpoint`'s
    own `since` is exactly the "last instant this monitor is known to
    have reached" every such monitor already tracks for its own
    purposes; this reuses that same value for a second purpose,
    detecting whether time passed with nobody watching).

    **Always a single, fully-formed, retroactive write — never an
    "open" gap with a start and no end.** A monitor's own process
    cannot write anything while it is not running, so the only moment
    a gap can ever be recorded is the moment collection resumes, with
    both ends already known: `checkpoint_until` (where coverage last
    reached) and `now` (this call's own instant, where coverage
    resumes). `ADR-0011` § 9's own wording, "once it resumes, an end",
    already names why: before resumption there is nothing to write,
    so every collection-gap fact that exists in the graph is, by
    construction, already a closed interval — never a currently-open
    one a still-down collector could not have written anyway.

    **`checkpoint_until=None` writes nothing.** A monitor's first run
    ever has no prior coverage to have gapped from — the same
    reasoning `aistack.cli.docker_events_monitor.run_cycle`'s own
    first-run handling already applies to its `since` boundary
    (`FIRST_RUN_LOOKBACK_SECONDS`, not an unbounded backfill,
    `ARC-P-006`): coverage simply begins now, nothing is missing yet.

    **No `end` field in the content — the same restraint
    `aistack.providers.docker.events_history.record_docker_events`'s
    own docstring already gives for `collected_at`.** The history
    filename `write_artifact_with_history` stamps with its own
    recording instant already states the gap's end; a second field
    inside the content could only repeat or drift from it.

    Returns `None`, writing nothing, when there is no real gap to
    record: a first run (`checkpoint_until` is `None`), or `now` at or
    before the checkpoint — the second case not expected in normal
    operation (a monitor's own checkpoint cannot run ahead of the
    real clock it was written against), kept as a defensive no-op
    rather than an assumption.
    """

    if checkpoint_until is None:
        return None

    if now.isoformat() <= checkpoint_until:
        return None

    content = (
        json.dumps({"stream": stream_stem, "start": checkpoint_until}, indent=2)
        + "\n"
    )
    output_path = generated_dir / "collection-gaps" / stream_stem / "collection-gap.json"
    latest_path, _ = write_artifact_with_history(content, output_path)
    return latest_path
