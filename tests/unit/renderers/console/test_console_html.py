from __future__ import annotations

from aistack.contracts.console_link import ConsoleLink
from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH, HealthScore
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.renderers.console.html import render_html


def selection_ui_link() -> ConsoleLink:
    return ConsoleLink(
        name="Selection UI",
        description="Sélection des candidats",
        url="http://GIGABYTE:8181",
    )


def health_link() -> ConsoleLink:
    return ConsoleLink(
        name="Cockpit Santé", description="Score de santé", url="/health.html"
    )


# --------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------


def test_the_document_is_a_self_contained_html_page():
    document = render_html((selection_ui_link(),))

    assert document.startswith("<!doctype html>")
    assert "<title>AIStack — Console</title>" in document
    assert document.strip().endswith("</html>")


def test_rendering_the_same_links_twice_is_byte_identical():
    links = (selection_ui_link(), health_link())

    assert render_html(links) == render_html(links)


def test_no_external_network_reference_is_present():
    """
    Same discipline `architecture.html`'s vendored mermaid.js and
    `health.html`'s script-free page already hold: this page must
    render correctly with no outbound internet, the normal state of
    the LAN it lives on — no `http(s)://` reference except the
    owner's own declared link targets.
    """

    document = render_html((selection_ui_link(),))

    assert "cdn." not in document
    assert "googleapis" not in document
    assert "<script" not in document


# --------------------------------------------------------------------
# Branding — the owner's own logo, vendored inline
# --------------------------------------------------------------------


def test_the_lockup_is_embedded_as_a_data_uri():
    document = render_html((selection_ui_link(),))

    assert 'src="data:image/png;base64,' in document


def test_the_mark_is_embedded_as_the_favicon():
    document = render_html((selection_ui_link(),))

    assert '<link rel="icon" href="data:image/png;base64,' in document


# --------------------------------------------------------------------
# Links — every declared ConsoleLink becomes one card
# --------------------------------------------------------------------


def test_every_link_becomes_one_card():
    links = (selection_ui_link(), health_link())

    document = render_html(links)

    assert document.count('<a class="card"') == 2
    assert "Selection UI" in document
    assert "Cockpit Santé" in document
    assert 'href="http://GIGABYTE:8181"' in document
    assert 'href="/health.html"' in document


def test_a_links_description_is_shown():
    document = render_html((selection_ui_link(),))

    assert "Sélection des candidats" in document


def test_html_special_characters_in_a_link_are_escaped():
    link = ConsoleLink(
        name="A & B <test>", description="x & y", url="/a?b=1&c=2"
    )

    document = render_html((link,))

    assert "A &amp; B &lt;test&gt;" in document
    assert "x &amp; y" in document
    assert "/a?b=1&amp;c=2" in document
    assert "<test>" not in document


def test_no_links_renders_an_empty_grid_not_an_error():
    document = render_html(())

    assert document.startswith("<!doctype html>")
    assert document.count('<a class="card"') == 0


# --------------------------------------------------------------------
# Health cartouche (PLAN-J11 § 11.9) — optional, backward compatible
# --------------------------------------------------------------------


def test_no_cockpit_renders_no_cartouche():
    """
    `cockpit=None` (every call before 2026-09-13) renders the page
    exactly as it always has — the same optional-parameter idiom
    `aistack.renderers.architecture.html.render_html` already holds
    for `topology`/`beszel_readings`/`dependency_graph`.
    """

    document = render_html((selection_ui_link(),))

    assert "État de santé du homelab" not in document
    assert '<section class="health-cartouche">' not in document


def test_a_cockpit_with_no_domains_renders_no_cartouche():
    document = render_html((selection_ui_link(),), cockpit=HealthCockpit(domains=()))

    assert "État de santé du homelab" not in document


def test_a_cockpit_renders_one_badge_per_domain():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True, findings=()),
            HealthDomain(name="Services", instrumented=False, note="pas encore"),
        )
    )

    document = render_html((selection_ui_link(),), cockpit=cockpit)

    assert "État de santé du homelab" in document
    assert "Stockage — rien à signaler" in document
    assert "Services — non instrumenté" in document
    assert 'href="/health.html"' in document
    assert "Voir le détail par domaine" in document


def test_a_domain_with_findings_shows_its_count():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(
                name="GPU",
                instrumented=True,
                findings=(_dummy_finding(), _dummy_finding()),
            ),
        )
    )

    document = render_html((selection_ui_link(),), cockpit=cockpit)

    assert "GPU — 2 finding(s)" in document
    assert "badge-alert" in document


def test_no_score_and_no_note_renders_no_score_line():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html((selection_ui_link(),), cockpit=cockpit)

    assert "Score de santé" not in document


def test_a_computed_score_is_shown_with_its_bucket():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = HealthScore(value=82, measured_domains=3, total_domains=4, bucket=TO_WATCH)

    document = render_html((selection_ui_link(),), cockpit=cockpit, score=score)

    assert "Score de santé : <strong>82/100</strong>" in document
    assert "à surveiller" in document
    assert "badge-watch" in document


def test_an_excellent_score_uses_the_clean_badge():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = HealthScore(value=100, measured_domains=4, total_domains=4, bucket=EXCELLENT)

    document = render_html((selection_ui_link(),), cockpit=cockpit, score=score)

    assert "badge-clean" in document


def test_an_action_required_score_uses_the_alert_badge():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = HealthScore(value=40, measured_domains=4, total_domains=4, bucket=ACTION_REQUIRED)

    document = render_html((selection_ui_link(),), cockpit=cockpit, score=score)

    assert "badge-alert" in document


def test_a_score_note_is_shown_when_the_score_could_not_be_computed():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(
        (selection_ui_link(),),
        cockpit=cockpit,
        score=None,
        score_note="no health-score weight definition at ...",
    )

    assert "Score de santé : non calculé" in document
    assert "no health-score weight definition" in document


def test_no_technical_debt_score_and_no_note_renders_no_line():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html((selection_ui_link(),), cockpit=cockpit)

    assert "Dette technique" not in document


def test_a_computed_technical_debt_score_is_shown_with_its_bucket():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = TechnicalDebtScore(value=85, findings=(), bucket=TO_WATCH)

    document = render_html(
        (selection_ui_link(),), cockpit=cockpit, technical_debt_score=score
    )

    assert "Dette technique : <strong>85/100</strong>" in document
    assert "badge-watch" in document


def test_an_excellent_technical_debt_score_uses_the_clean_badge():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = TechnicalDebtScore(value=100, findings=(), bucket=EXCELLENT)

    document = render_html(
        (selection_ui_link(),), cockpit=cockpit, technical_debt_score=score
    )

    assert "badge-clean" in document


def test_an_action_required_technical_debt_score_uses_the_alert_badge():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = TechnicalDebtScore(value=0, findings=(), bucket=ACTION_REQUIRED)

    document = render_html(
        (selection_ui_link(),), cockpit=cockpit, technical_debt_score=score
    )

    assert "badge-alert" in document


def test_a_technical_debt_note_is_shown_when_the_score_could_not_be_computed():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(
        (selection_ui_link(),),
        cockpit=cockpit,
        technical_debt_score=None,
        technical_debt_note="no health-score weight definition available; "
        "technical-debt score is not computed",
    )

    assert "Dette technique : non calculée" in document
    assert "no health-score weight definition" in document


def test_the_technical_debt_line_appears_right_after_the_global_score():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = HealthScore(value=82, measured_domains=3, total_domains=4, bucket=TO_WATCH)
    debt_score = TechnicalDebtScore(value=100, findings=(), bucket=EXCELLENT)

    document = render_html(
        (selection_ui_link(),),
        cockpit=cockpit,
        score=score,
        technical_debt_score=debt_score,
    )

    assert document.index("Score de santé") < document.index("Dette technique")


def test_a_domains_name_in_the_cartouche_is_html_escaped():
    cockpit = HealthCockpit(
        domains=(HealthDomain(name="<script>alert(1)</script>", instrumented=True),)
    )

    document = render_html((selection_ui_link(),), cockpit=cockpit)

    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;" in document


def test_rendering_the_same_cockpit_twice_is_byte_identical():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True, findings=(_dummy_finding(),)),
        )
    )
    score = HealthScore(value=90, measured_domains=1, total_domains=4, bucket=EXCELLENT)

    links = (selection_ui_link(),)

    assert render_html(links, cockpit=cockpit, score=score) == render_html(
        links, cockpit=cockpit, score=score
    )


def _dummy_finding():
    from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
    from aistack.contracts.storage_reading import StorageReading

    return RuntimeFinding(
        subject="/",
        signature="OPS-0004",
        interpretation="x",
        remediation="y",
        confidence="Measured",
        grounding="unknown",
        evidence=(
            CitedReading(
                provider="aistack.provider.storage",
                reading=StorageReading(
                    mount="/", total_bytes=100, used_bytes=99, free_bytes=1
                ),
            ),
        ),
    )
