"""AIStack's data against its disk budget, and the compaction (ADR-0021, 2026-10-09)."""

from __future__ import annotations

import gzip
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.cli import data_budget as cli
from aistack.data_budget.budget import (
    DataBudget,
    compact_if_due,
    compress_old,
    load_data_budget,
    measure,
)
from aistack.data_budget.health import evaluate_data_usage
from aistack.history import every_version, latest_observations
from aistack.i18n import translator_for

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
BUDGET = DataBudget(budget_bytes=10_000, warn_percent=80, compress_after=timedelta(days=90), compress=("docker-diff",))


def _stream(root: Path, stamps: list[str]) -> Path:
    history = root / "docker-diff" / "nginx" / "history" / "docker-diff"
    history.mkdir(parents=True)
    for stamp in stamps:
        (history / f"{stamp}.json").write_text(json.dumps({"at": stamp, "files": ["a"] * 50}), encoding="utf-8")
    (root / "docker-diff" / "nginx" / "docker-diff.json").write_text("{}", encoding="utf-8")
    return history


def test_the_shipped_budget_is_the_owners() -> None:
    budget = load_data_budget()
    assert budget.budget_bytes == 2048 * 1024 * 1024
    assert budget.compress_after == timedelta(days=90)
    assert budget.compress == ("history", "docker-diff", "docker-events")


def test_old_observations_are_compressed_and_still_read_the_same(tmp_path: Path) -> None:
    history = _stream(tmp_path, ["2026-05-01T10-00-00Z", "2026-05-01T10-00-00Z-1", "2026-10-01T10-00-00Z"])
    before = [o.read() for o in every_version(tmp_path / "docker-diff" / "nginx", "docker-diff")]

    done = compress_old(tmp_path, BUDGET, NOW)

    assert done.files == 2 and done.after < done.before and done.problems == []
    names = sorted(p.name for p in history.iterdir())
    assert names == ["2026-05-01T10-00-00Z-1.json.gz", "2026-05-01T10-00-00Z.json.gz", "2026-10-01T10-00-00Z.json"]
    after = every_version(tmp_path / "docker-diff" / "nginx", "docker-diff")
    assert [o.read() for o in after] == before
    assert [o.rank for o in after] == [0, 1, 0]
    assert len(latest_observations(tmp_path / "docker-diff" / "nginx", "docker-diff")) == 2
    # The latest file beside history/ is never touched.
    assert (tmp_path / "docker-diff" / "nginx" / "docker-diff.json").exists()
    # A second run has nothing left to do.
    assert compress_old(tmp_path, BUDGET, NOW).files == 0


def test_a_dry_run_changes_nothing(tmp_path: Path) -> None:
    history = _stream(tmp_path, ["2026-05-01T10-00-00Z"])
    done = compress_old(tmp_path, BUDGET, NOW, dry_run=True)
    assert done.files == 1 and done.after < done.before
    assert [p.name for p in history.iterdir()] == ["2026-05-01T10-00-00Z.json"]


def test_an_interrupted_run_is_finished(tmp_path: Path) -> None:
    history = _stream(tmp_path, ["2026-05-01T10-00-00Z"])
    plain = history / "2026-05-01T10-00-00Z.json"
    with gzip.open(history / "2026-05-01T10-00-00Z.json.gz", "wb") as stream:
        stream.write(plain.read_bytes())
    assert compress_old(tmp_path, BUDGET, NOW).files == 1
    assert not plain.exists()


def test_directories_not_declared_are_left_alone(tmp_path: Path) -> None:
    other = tmp_path / "docker-digest" / "x" / "history" / "docker-digest"
    other.mkdir(parents=True)
    (other / "2026-01-01T00-00-00Z.json").write_text("{}", encoding="utf-8")
    assert compress_old(tmp_path, BUDGET, NOW).files == 0


def test_compaction_runs_at_most_once_a_day(tmp_path: Path) -> None:
    _stream(tmp_path, ["2026-05-01T10-00-00Z"])
    assert compact_if_due(tmp_path, BUDGET, NOW) is not None
    assert compact_if_due(tmp_path, BUDGET, NOW + timedelta(hours=3)) is None
    assert compact_if_due(tmp_path, BUDGET, NOW + timedelta(days=1)) is not None


def test_measure_adds_up_and_finds_the_pace(tmp_path: Path) -> None:
    (tmp_path / "big").mkdir()
    (tmp_path / "big" / "a").write_bytes(b"x" * 7000)
    old = tmp_path / "old"
    old.write_bytes(b"y" * 1000)
    stamp = (NOW - timedelta(days=30)).timestamp()
    os.utime(old, (stamp, stamp))

    reading = measure(tmp_path, BUDGET)
    assert reading.used_bytes == 8000 and reading.files == 2
    assert reading.largest[0] == ("big", 7000)
    assert reading.percent == 80
    assert reading.daily_bytes == 1000  # 7000 written this week, a day on average


def test_findings_near_and_over_the_budget(tmp_path: Path) -> None:
    (tmp_path / "big").mkdir()
    (tmp_path / "big" / "a").write_bytes(b"x" * 5000)
    assert evaluate_data_usage(measure(tmp_path, BUDGET)) == ()

    (tmp_path / "big" / "b").write_bytes(b"x" * 3500)
    (near,) = evaluate_data_usage(measure(tmp_path, BUDGET))
    assert "85 % of its budget" in near.interpretation and near.qualifications == ("OPS-0004/sustainability-anomaly",)

    (tmp_path / "big" / "c").write_bytes(b"x" * 2000)
    (over,) = evaluate_data_usage(measure(tmp_path, BUDGET))
    assert "past its budget" in over.interpretation

    t = translator_for("en")
    for finding in (near, over):
        assert finding.message is not None
        assert " ".join(t(p.key, **dict(p.params)) for p in finding.message.interpretation) == finding.interpretation
        assert " ".join(t(p.key, **dict(p.params)) for p in finding.message.remediation) == finding.remediation


def test_the_command_reports_and_compresses(tmp_path: Path, capsys, monkeypatch) -> None:
    _stream(tmp_path, ["2026-05-01T10-00-00Z"])
    monkeypatch.setattr(cli, "load_data_budget", lambda: BUDGET)
    assert cli.main(["--compress"], generated=tmp_path) == 0
    out = capsys.readouterr().out
    assert "Données d'AIStack" in out and "compressées : 1" in out
