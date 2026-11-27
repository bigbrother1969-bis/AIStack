"""How AIStack itself is doing: the engine's calls, the anomalies left without words, the length of a pass (ADR-0032, O10)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.boot_checks.explain import RULES  # noqa: F401  (the module imports cleanly beside the measure)
from aistack.boot_checks.quality import CALLER, Quality, read_quality, unexplained
from aistack.boot_checks.state import Explanation, Verdict, read_verdict, write_verdict

NOW = datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class FakeCall:
    at: str
    caller: str = CALLER
    operation: str = "explain"
    reachable: bool = True
    seconds: float = 80.0


def _at(days: float) -> str:
    return (NOW - timedelta(days=days)).isoformat()


def test_only_the_calls_of_the_checks_in_the_window_count() -> None:
    calls = [
        FakeCall(_at(1), seconds=40.0),
        FakeCall(_at(2), operation="choose", seconds=100.0, reachable=False),
        FakeCall(_at(3), seconds=70.0),
        FakeCall(_at(30), seconds=999.0),
        FakeCall(_at(1), caller="troubleshooting"),
        FakeCall(_at(1), operation="reason"),
        FakeCall("not a date"),
    ]
    seen = read_quality(calls, NOW, 7, 3)

    assert (seen.calls, seen.answered, seen.median, seen.slowest) == (3, 2, 70.0, 100.0)
    assert seen.enough


def test_too_few_calls_say_so_instead_of_a_rate() -> None:
    seen = read_quality([FakeCall(_at(1)), FakeCall(_at(2))], NOW, 7, 5)

    assert seen.calls == 2 and not seen.enough
    assert read_quality([], NOW, 7, 5) == Quality(days=7, min_calls=5) and not read_quality([], NOW, 7, 5).enough


def test_a_naive_date_is_read_as_utc() -> None:
    naive = (NOW - timedelta(days=1)).replace(tzinfo=None).isoformat()

    assert read_quality([FakeCall(naive)], NOW, 7, 1).calls == 1


def test_an_anomaly_asked_and_not_answered_is_a_marker() -> None:
    said = Explanation("disks", "warning", "x", "dit", "m", NOW.isoformat())

    assert unexplained((said, replace(said, text=""), replace(said, text=""))) == 2 and unexplained(()) == 0


def test_the_duration_of_a_pass_is_kept_and_an_old_verdict_reads_without_it(tmp_path: Path) -> None:
    verdict = Verdict("ok", 0, NOW.isoformat(), "b", None, (), took=12.5)
    write_verdict(tmp_path, verdict)
    stored = read_verdict(tmp_path)

    assert stored is not None and stored.took == 12.5

    text = (tmp_path / "boot-check.json").read_text(encoding="utf-8").replace('"took": 12.5', '"took": true')
    (tmp_path / "boot-check.json").write_text(text, encoding="utf-8")
    again = read_verdict(tmp_path)

    assert again is not None and again.took is None
