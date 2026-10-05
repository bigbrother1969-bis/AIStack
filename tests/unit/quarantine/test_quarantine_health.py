"""The quarantine on the health page (`OPS-0012`): counted as technical
debt, shown as one line in the card."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from aistack.cli import console_render, health_render
from aistack.contracts.health_score import EXCELLENT, TO_WATCH, DomainWeight, HealthScoreWeights
from aistack.contracts.quarantine_reading import READY, USED, WATCHED, QuarantineReading
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.quarantine import quarantine_findings
from aistack.quarantine.register import QuarantineEntry
from aistack.quarantine.status import statuses
from aistack.renderers.health.html import render_html
from aistack.runtime.evaluate_quarantine import evaluate_quarantine

WEIGHTS = HealthScoreWeights(weights=(DomainWeight(domain="Services", points=15),))
COCKPIT = HealthCockpit(domains=(HealthDomain(name="Services", instrumented=True),))
ENTRY = QuarantineEntry(
    id="Q-1", paths=("src/aistack/old/",), reason="dead", since=date(2026, 10, 5), review_after=date(2026, 11, 16)
)


def _reading(entry: str, state: str, uses: int = 0) -> QuarantineReading:
    return QuarantineReading(
        entry=entry,
        paths=(f"{entry.lower()}/",),
        since=date(2026, 10, 5),
        review_after=date(2026, 11, 16),
        state=state,
        uses=uses,
        last_use="2026-10-20T03:00:00+02:00" if uses else "",
    )


def test_the_quarantine_costs_one_domain_of_debt() -> None:
    findings = evaluate_quarantine(statuses((ENTRY, replace(ENTRY, id="Q-2")), (), date(2026, 10, 6)))
    for cli in (health_render, console_render):
        score, note = cli.technical_debt_score(COCKPIT, WEIGHTS, findings)
        assert note == ""
        assert score is not None
        assert score.value == 85
        assert len(score.findings) == 2


def test_without_a_quarantine_nothing_changes() -> None:
    score, _ = health_render.technical_debt_score(COCKPIT, WEIGHTS)
    assert score is not None and score.value == 100


def test_the_shipped_register_is_read_for_the_page() -> None:
    findings, readings, note = quarantine_findings(date(2026, 10, 6))
    assert note == ""
    assert len(findings) == len(readings) > 0


def test_the_card_says_what_is_in_quarantine() -> None:
    score = TechnicalDebtScore(value=85, findings=(), bucket=TO_WATCH)
    readings = (_reading("Q-1", WATCHED), _reading("Q-2", USED, uses=2), _reading("Q-3", READY))
    page = render_html(COCKPIT, technical_debt_score=score, quarantine=readings, lang="fr")
    assert "Code en quarantaine : 3 élément(s), révision le 16/11/2026 — 2 utilisation(s) constatée(s)." in page
    assert "Q-2 (q-2/) : utilisé 2 fois, la dernière le 2026-10-20T03:00:00+02:00 — à sortir de la quarantaine" in page
    assert "Q-3 (q-3/) : jamais utilisé — prêt à effacer" in page
    assert "Q-1 (" not in page
    english = render_html(COCKPIT, technical_debt_score=score, quarantine=readings, lang="en")
    assert "Code in quarantine: 3 item(s), review on 2026-11-16 — 2 use(s) recorded." in english


def test_an_unreadable_register_is_named_and_an_empty_one_is_silent() -> None:
    score = TechnicalDebtScore(value=100, findings=(), bucket=EXCELLENT)
    page = render_html(COCKPIT, technical_debt_score=score, quarantine_note="boom", lang="fr")
    assert "Code en quarantaine : registre illisible — boom" in page
    assert "quarantaine" not in render_html(COCKPIT, technical_debt_score=score, lang="fr")
