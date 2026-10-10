"""`plan.html`, and the badges that open it (2026-10-08)."""

from __future__ import annotations

from aistack.contracts.health_score import ACTION_REQUIRED, TO_WATCH, HealthScore
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.plan import debt_plan, health_plan
from aistack.renderers.console.html import render_html as render_console
from aistack.renderers.health.html import render_html as render_health
from aistack.renderers.plan.html import render_plan
from tests.unit.health.test_plan import COCKPIT, WEIGHTS
from tests.unit.web.test_every_control_has_a_tooltip import untitled

SCORE = HealthScore(value=81, measured_domains=3, total_domains=3, bucket=TO_WATCH)
DEBT = TechnicalDebtScore(value=70, findings=(), bucket=ACTION_REQUIRED)


def page(lang: str = "fr", base_url: str | None = "http://gigabyte:8186/troubleshooting") -> str:
    return render_plan(
        health_plan(COCKPIT, WEIGHTS),
        debt_plan(COCKPIT, 15),
        score=SCORE,
        debt_score=DEBT,
        weight=15,
        subject_counts={},
        troubleshooting_base_url=base_url,
        lang=lang,
    )


def test_the_plan_ranks_and_says_how_and_what_it_gains():
    text = page()

    assert 'id="sante"' in text and 'id="dette"' in text
    assert "Score de santé : 81/100 (à surveiller)." in text
    assert "+50 points quand ce domaine" in text
    assert "il faut les corriger tous" in text
    assert "./config/pra_tests.yml" in text and "scripts/restore_aistack.sh" in text
    assert 'href="http://gigabyte:8186/troubleshooting/#finding-wordpress"' in text
    assert untitled(text) == []


def test_the_plan_reads_in_english_too():
    text = page("en")

    assert "Raise the health score" in text and "Reduce the technical debt" in text
    assert "Health score: 81/100 (to watch)." in text


def test_without_scores_the_plan_says_why():
    text = render_plan((), (), score=None, score_note="no weights", debt_score=None, debt_note="no weights", lang="en")

    assert "Health score not computed — no weights" in text
    assert "Technical debt not computed — no weights" in text


def test_both_badges_open_the_plan_on_the_console_and_the_health_cockpit():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Services", instrumented=True),))
    health = render_health(cockpit, score=SCORE, technical_debt_score=DEBT, lang="fr")
    assert 'href="/plan.html?lang=fr#sante"' in health
    assert 'href="/plan.html?lang=fr#dette"' in health

    console = render_console([], cockpit=cockpit, score=SCORE, technical_debt_score=DEBT, lang="en")
    assert 'href="/plan.html?lang=en#sante"' in console
    assert 'href="/plan.html?lang=en#dette"' in console
