"""
The query layer's CLI, `python -m aistack.cli.history_query` —
the terminal-usable half of the shape chosen 2026-09-03 alongside
the `aistack.history` library (`claude/ROADMAP-SYNTHESIS-2026-09-03.md`
follow-up: "La couche de requête").

Driven as a subprocess against a real `reports/generated/` tree,
the same way `test_knowledge_integrity_output.py` drives its CLI —
what's under test is the wiring from argv to the library, not the
library's own logic (covered by `tests/unit/history/test_query.py`).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aistack.generators.history import write_artifact_with_history


ROOT = Path(__file__).parents[3]


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "aistack.cli.history_query", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
    )


def test_with_no_history_at_all_it_says_so(tmp_path: Path):
    result = _run(tmp_path)

    assert result.returncode == 0
    assert "No Observation History" in result.stdout


def test_it_lists_stems_with_how_many_instants_each_has(tmp_path: Path):
    # Two real-clock writes can land in the same wall-clock second
    # (`available_instants` collapses those on purpose — see
    # `tests/unit/history/test_query.py`), so this only asserts the
    # stem is listed with a count, not a specific number.
    write_artifact_with_history("a\n", tmp_path / "reports" / "generated" / "docker-runtime-catalog.json")

    result = _run(tmp_path)

    assert result.returncode == 0
    assert "docker-runtime-catalog (1 observed)" in result.stdout


def test_it_lists_the_instants_a_named_stem_was_observed_at(tmp_path: Path):
    write_artifact_with_history("a\n", tmp_path / "reports" / "generated" / "docker-runtime-catalog.json")

    result = _run(tmp_path, "docker-runtime-catalog")

    assert result.returncode == 0
    assert "was observed at:" in result.stdout
    assert result.stdout.count("- 20") == 1


def test_it_fails_clearly_when_asked_for_an_unobserved_stem(tmp_path: Path):
    result = _run(tmp_path, "never-written")

    assert result.returncode == 2
    assert "never-written" in result.stdout


def test_it_prints_the_content_current_at_or_before_the_given_instant(tmp_path: Path):
    output_path = tmp_path / "reports" / "generated" / "docker-runtime-catalog.json"
    write_artifact_with_history('{"n": 1}\n', output_path)

    history_dir = output_path.parent / "history" / "docker-runtime-catalog"
    written_at = next(history_dir.glob("*.json")).stem

    result = _run(tmp_path, "docker-runtime-catalog", written_at)

    assert result.returncode == 0
    assert '{"n": 1}' in result.stdout
    assert written_at in result.stdout


def test_it_fails_clearly_for_an_instant_before_the_first_observation(tmp_path: Path):
    write_artifact_with_history("a\n", tmp_path / "reports" / "generated" / "docker-runtime-catalog.json")

    result = _run(tmp_path, "docker-runtime-catalog", "2000-01-01T00-00-00Z")

    assert result.returncode == 1
    assert "No observation" in result.stdout


def test_it_rejects_an_instant_in_the_wrong_shape(tmp_path: Path):
    write_artifact_with_history("a\n", tmp_path / "reports" / "generated" / "docker-runtime-catalog.json")

    result = _run(tmp_path, "docker-runtime-catalog", "2026-09-03T18:05:00Z")

    assert result.returncode == 2
    assert "not an instant" in result.stdout
