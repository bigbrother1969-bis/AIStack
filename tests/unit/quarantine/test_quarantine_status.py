from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from aistack.cli.quarantine_report import report
from aistack.contracts.quarantine_reading import READY, USED, WATCHED, QuarantineReading
from aistack.contracts.runtime_finding import CitedReading
from aistack.quarantine.hits import Hit
from aistack.quarantine.register import QuarantineEntry
from aistack.quarantine.status import statuses
from aistack.runtime.evaluate_quarantine import evaluate_quarantine

MODULE = QuarantineEntry(
    id="Q-1", paths=("src/aistack/old/",), reason="dead", since=date(2026, 10, 5), review_after=date(2026, 11, 16)
)
SCRIPT = QuarantineEntry(
    id="Q-2", paths=("scripts/old.sh",), reason="dead", since=date(2026, 10, 5), review_after=date(2026, 11, 16),
    amend=("README.md",),
)
USE = Hit(at="2026-10-20T03:00:00+02:00", kind="script", target="scripts/old.sh", caller="cron", program="/bin/sh -c")


def test_an_item_is_watched_until_its_review() -> None:
    (status,) = statuses((MODULE,), (), date(2026, 11, 15))
    assert status.state == WATCHED


def test_an_item_never_used_is_ready_at_its_review() -> None:
    (status,) = statuses((MODULE,), (), date(2026, 11, 16))
    assert status.state == READY


def test_one_use_takes_an_item_out_whatever_the_date() -> None:
    found = statuses((MODULE, SCRIPT), (USE, Hit(at="x", kind="module", target="aistack.old.sub", caller="y")), date(2026, 12, 1))
    assert [(status.entry.id, status.state, len(status.hits)) for status in found] == [
        ("Q-1", USED, 1),
        ("Q-2", USED, 1),
    ]


def test_a_use_of_something_else_is_ignored() -> None:
    (status,) = statuses((MODULE,), (Hit(at="x", kind="module", target="aistack.older", caller="y"),), date(2026, 10, 6))
    assert status.state == WATCHED


@pytest.mark.parametrize("state,uses", [(USED, 0), (WATCHED, 1), ("gone", 0)])
def test_a_reading_that_contradicts_itself_is_refused(state: str, uses: int) -> None:
    with pytest.raises(ValueError):
        QuarantineReading(
            entry="Q-1", paths=("a",), since=date(2026, 10, 5), review_after=date(2026, 11, 16), state=state, uses=uses
        )


def test_every_item_is_technical_debt_and_nothing_else() -> None:
    found = statuses((MODULE, SCRIPT), (USE,), date(2026, 10, 21))
    findings = evaluate_quarantine(found)
    assert [finding.subject for finding in findings] == ["Q-1", "Q-2"]
    assert {finding.qualifications for finding in findings} == {("OPS-0004/technical-debt",)}
    assert findings[0].remediation.startswith("Nothing before 2026-11-16")
    assert "not dead code" in findings[1].interpretation
    evidence = findings[1].evidence[0]
    assert isinstance(evidence, CitedReading)
    assert isinstance(evidence.reading, QuarantineReading)
    assert evidence.reading.last_use == USE.at


def test_a_ready_item_says_to_delete_it() -> None:
    (finding,) = evaluate_quarantine(statuses((SCRIPT,), (), date(2026, 11, 16)))
    assert finding.remediation.startswith("Delete Q-2's files")


def test_the_report_lists_states_uses_and_amendments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "aistack.cli.quarantine_report.read_statuses",
        lambda today: statuses((MODULE, SCRIPT), (USE,), today),
    )
    (tmp_path / "src/aistack/old").mkdir(parents=True)
    text = report(date(2026, 10, 21), tmp_path)
    assert "Q-1  surveillé jusqu'au 2026-11-16" in text
    assert "Q-2  UTILISÉ  —  1 utilisation(s)" in text
    assert "scripts/old.sh   (ABSENT)" in text
    assert "! 2026-10-20T03:00:00+02:00  scripts/old.sh  par cron" in text
    assert "à amender à l'effacement : README.md" in text
    assert text.endswith("2 élément(s) : 1 utilisé(s), 0 prêt(s) à effacer")
