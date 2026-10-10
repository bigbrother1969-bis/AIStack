from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from aistack.generators.history import write_artifact_with_history

# One root per stream, outside `generated_dir`'s flat `history/`, so
# `available_stems(generated_dir)` never mixes a stream's observations
# with its collection-gap facts.
DEFAULT_COLLECTION_GAPS_ROOT = Path("reports/generated") / "collection-gaps"


def record_collection_gap(
    stream_stem: str,
    *,
    checkpoint_until: str | None,
    now: datetime,
    generated_dir: Path = Path("reports/generated"),
) -> Path | None:
    """
    Record a collection gap for `stream_stem` (`ADR-0011` § 9). Each
    monitor calls this once at startup with its last checkpoint.

    The gap is written once, closed, when collection resumes: it starts
    at `checkpoint_until`, and its end is the history copy's timestamp
    (so the content has no `end` field).

    Returns the written path, or `None` when there is no gap: a first
    run (`checkpoint_until` is `None`) or `now` not after the checkpoint.
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
