"""
CPU decision history — `aistack.priority.decision_history`, scoped
2026-09-03 against two trade-offs put to the owner:

- **Cadence: on change only** (`ApplyReport.changed`), not every
  5-second poll — the same condition `log_cycle` already prints on.
- **Content: state and report**, not a raw detector reading —
  `Detector.is_active()` exposes only a bool; extending that shared
  Protocol was declined in favour of shipping what today's shape
  already computes.

`record_decision`/`serialize_decision` are pure and file-writing,
not host-touching (no Docker, no HTTP) — unlike `apply_resource
_priority` and the detectors, this is fully covered here rather than
verified live.
"""

from __future__ import annotations

import json
from pathlib import Path

from aistack.priority.apply import ApplyReport
from aistack.priority.decision_history import (
    DEFAULT_OUTPUT_PATH,
    record_decision,
    serialize_decision,
)


def test_serialize_decision_carries_every_outcome_bucket():
    report = ApplyReport(
        applied=("jellyfin",),
        unchanged=("radarr",),
        not_found=("qbittorrent",),
        failed=(("sonarr", "permission denied"),),
        dry_run=True,
    )

    serialized = serialize_decision(
        boosted={"jellyfin": True, "radarr": False}, report=report
    )

    assert serialized["boosted"] == {"jellyfin": True, "radarr": False}
    assert serialized["applied"] == ["jellyfin"]
    assert serialized["unchanged"] == ["radarr"]
    assert serialized["not_found"] == ["qbittorrent"]
    assert serialized["failed"] == [["sonarr", "permission denied"]]
    assert serialized["dry_run"] is True


def test_serialize_decision_stamps_an_iso_timestamp():
    serialized = serialize_decision(boosted={}, report=ApplyReport())

    assert serialized["observed_at"][:4].isdigit()
    assert "T" in serialized["observed_at"]


def test_the_result_is_actually_json_serializable():
    serialized = serialize_decision(
        boosted={"jellyfin": True},
        report=ApplyReport(applied=("jellyfin",)),
    )

    json.dumps(serialized)


def test_record_decision_writes_nothing_when_the_report_did_not_change(
    tmp_path: Path,
):
    output_path = tmp_path / "resource-priority-decision.json"

    written = record_decision(
        boosted={"jellyfin": False},
        report=ApplyReport(unchanged=("jellyfin",)),
        output_path=output_path,
    )

    assert written is None
    assert not output_path.exists()


def test_record_decision_writes_the_latest_path_on_a_real_change(tmp_path: Path):
    output_path = tmp_path / "resource-priority-decision.json"

    written = record_decision(
        boosted={"jellyfin": True},
        report=ApplyReport(applied=("jellyfin",)),
        output_path=output_path,
    )

    assert written == output_path
    content = json.loads(output_path.read_text(encoding="utf-8"))
    assert content["boosted"] == {"jellyfin": True}


def test_record_decision_keeps_history_like_every_other_historicised_artifact(
    tmp_path: Path,
):
    output_path = tmp_path / "resource-priority-decision.json"

    record_decision(
        boosted={"jellyfin": True},
        report=ApplyReport(applied=("jellyfin",)),
        output_path=output_path,
    )
    record_decision(
        boosted={"jellyfin": False},
        report=ApplyReport(applied=("jellyfin",)),
        output_path=output_path,
    )

    history_dir = output_path.parent / "history" / output_path.stem
    assert len(list(history_dir.glob("*.json"))) == 2


def test_record_decision_does_not_write_history_when_unchanged(tmp_path: Path):
    """
    The other half of "on change only": a `record_decision` call
    that writes nothing to the latest path must not leave a history
    entry either — the two are one write, not two independent ones.
    """

    output_path = tmp_path / "resource-priority-decision.json"

    record_decision(
        boosted={"jellyfin": True},
        report=ApplyReport(applied=("jellyfin",)),
        output_path=output_path,
    )
    record_decision(
        boosted={"jellyfin": True},
        report=ApplyReport(unchanged=("jellyfin",)),
        output_path=output_path,
    )

    history_dir = output_path.parent / "history" / output_path.stem
    assert len(list(history_dir.glob("*.json"))) == 1


def test_default_output_path_matches_reports_generated_convention():
    assert DEFAULT_OUTPUT_PATH == Path(
        "reports/generated/resource-priority-decision.json"
    )
