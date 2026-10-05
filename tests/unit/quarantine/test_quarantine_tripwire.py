from __future__ import annotations

import json
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from aistack.quarantine.hits import read_hits
from aistack.quarantine.tripwire import QuarantinedCodeUsed, inspecting, record, tripwire

ROOT = Path(__file__).resolve().parents[3]


def test_the_test_suite_does_not_trip_it(tmp_path: Path) -> None:
    hits = tmp_path / "hits.jsonl"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        tripwire("aistack.old", hits)
    assert not hits.exists()


def test_a_use_is_recorded_and_warned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "pytest")
    hits = tmp_path / "quarantine" / "hits.jsonl"
    with pytest.warns(QuarantinedCodeUsed):
        tripwire("aistack.old", hits)
    (hit,) = read_hits(hits)
    assert hit.target == "aistack.old"
    assert hit.kind == "module"


def test_a_hits_file_that_cannot_be_written_stops_nothing(tmp_path: Path) -> None:
    blocked = tmp_path / "file"
    blocked.write_text("", encoding="utf-8")
    record("aistack.old", "module", "x", blocked / "hits.jsonl")


def test_a_line_that_cannot_be_read_is_skipped(tmp_path: Path) -> None:
    hits = tmp_path / "hits.jsonl"
    hits.write_text('not json\n{"kind": "module"}\n' + json.dumps({"target": "a.sh", "kind": "script"}) + "\n", encoding="utf-8")
    assert [hit.target for hit in read_hits(hits)] == ["a.sh"]
    assert read_hits(tmp_path / "absent.jsonl") == ()


def test_a_quarantined_module_imported_by_a_program_is_recorded(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import aistack.engines"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "OPS-0012" in result.stderr
    (hit,) = read_hits(tmp_path / "reports/generated/quarantine/hits.jsonl")
    assert hit.target == "aistack.engines"
    assert hit.caller == "<string>:1"


def _run_script(root: Path, env_line: str | None) -> Path:
    (root / "scripts").mkdir()
    (root / "scripts" / "quarantine_tripwire.sh").write_text(
        (ROOT / "scripts" / "quarantine_tripwire.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    if env_line is not None:
        (root / ".env").write_text(env_line + "\n", encoding="utf-8")
    result = subprocess.run(
        ["bash", "-c", f'source "{root}/scripts/quarantine_tripwire.sh"; quarantine_tripwire scripts/old.sh; echo done'],
        cwd="/",
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "done"
    assert "OPS-0012" in result.stderr
    return root


def test_a_quarantined_script_records_its_run(tmp_path: Path) -> None:
    root = _run_script(tmp_path, None)
    (hit,) = read_hits(root / "reports/generated/quarantine/hits.jsonl")
    assert (hit.kind, hit.target) == ("script", "scripts/old.sh")


def test_a_quarantined_script_records_into_the_compose_data_directory(tmp_path: Path) -> None:
    root = _run_script(tmp_path, "AISTACK_DATA_DIR=./data")
    (hit,) = read_hits(root / "data/quarantine/hits.jsonl")
    assert hit.target == "scripts/old.sh"


def test_an_inventory_of_the_code_is_not_a_use(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "pytest")
    hits = tmp_path / "hits.jsonl"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with inspecting():
            tripwire("aistack.old", hits)
    assert not hits.exists()


def test_the_context_bundle_export_trips_nothing(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, "-c", "from aistack.conformance.inventory import take_inventory; take_inventory()"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert not (tmp_path / "reports").exists()
