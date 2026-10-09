from __future__ import annotations

from aistack.contracts.console_link import LAN, PUBLIC, ConsoleLink
from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH, HealthScore
from aistack.contracts.technical_debt_score import TechnicalDebtScore
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.renderers.console.html import render_html


def selection_ui_link() -> ConsoleLink:
    return ConsoleLink(
        name="Selection UI",
        description="Sélection des candidats",
        url="http://GIGABYTE:8181",
        scope=LAN,
    )


def health_link() -> ConsoleLink:
    return ConsoleLink(
        name="Cockpit Santé",
        description="Score de santé",
        url="/health.html",
        scope=PUBLIC,
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


def test_the_page_declares_a_viewport():
    """
    Added 2026-09-30
    (`claude/AUDIT-CONSOLE-ARCHITECTURE-HEALTH-2026-09-29.md`, constat
    1): without it, a phone loads this page at desktop scale and then
    shrinks it to fit, forcing a zoom — Time Machine's own screens
    already carried this tag.
    """

    document = render_html((selection_ui_link(),))

    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in document


# --------------------------------------------------------------------
# Links — every declared ConsoleLink becomes one card
# --------------------------------------------------------------------


def test_every_link_becomes_one_card():
    links = (selection_ui_link(), health_link())

    document = render_html(links)

    assert document.count('<a class="card ') == 2
    assert "Selection UI" in document
    assert "Cockpit Santé" in document
    # ADR-0010 (2026-09-27): an absolute link — a mini-app on another
    # host — carries the language, since the console's cookie cannot
    # follow it there; a relative page of the console itself does not
    # need to.
    assert 'href="http://GIGABYTE:8181?lang=fr"' in document
    assert 'href="/health.html"' in document


def test_a_links_description_is_shown():
    document = render_html((selection_ui_link(),))

    assert "Sélection des candidats" in document


def test_html_special_characters_in_a_link_are_escaped():
    link = ConsoleLink(
        name="A & B <test>", description="x & y", url="/a?b=1&c=2", scope=PUBLIC
    )

    document = render_html((link,))

    assert "A &amp; B &lt;test&gt;" in document
    assert "x &amp; y" in document
    assert "/a?b=1&amp;c=2" in document
    assert "<test>" not in document


def test_no_links_renders_an_empty_grid_not_an_error():
    document = render_html(())

    assert document.startswith("<!doctype html>")
    assert document.count('<a class="card ') == 0


# --------------------------------------------------------------------
# Scope grouping (2026-09-30) — the owner: "un bandeau de couleur
# différent pour les cartes accessibles sur le réseau local ou depuis
# internet et on regroupera les cartes 'LAN' et les cartes 'Internet'"
# --------------------------------------------------------------------


def test_a_lan_and_a_public_card_are_placed_in_different_groups():
    document = render_html((selection_ui_link(), health_link()))

    assert document.count('<details class="link-group') == 2
    assert 'class="link-group link-group-lan"' in document
    assert 'class="link-group link-group-public"' in document


def test_each_group_shows_its_title_and_count():
    document = render_html((selection_ui_link(), health_link()))

    assert "Accessible depuis le réseau local" in document
    assert "Accessible depuis internet" in document
    assert document.count('<span class="link-group-count">1</span>') == 2


def test_a_group_with_no_cards_of_that_scope_is_not_rendered():
    document = render_html((selection_ui_link(),))

    assert "link-group-lan" in document
    assert "link-group-public" not in document
    assert "Accessible depuis internet" not in document


def test_a_card_carries_its_scope_as_a_css_class():
    document = render_html((selection_ui_link(), health_link()))

    assert '<a class="card card-lan"' in document
    assert '<a class="card card-public"' in document


def test_several_cards_of_the_same_scope_share_one_group():
    other_lan_link = ConsoleLink(
        name="Priorité CPU",
        description="Arbitrage de priorité CPU",
        url="http://GIGABYTE:8182",
        scope=LAN,
    )

    document = render_html((selection_ui_link(), other_lan_link, health_link()))

    assert document.count('<details class="link-group') == 2
    assert document.count('<span class="link-group-count">2</span>') == 1
    assert document.count('<span class="link-group-count">1</span>') == 1


def test_the_groups_are_folded_open_by_default():
    """
    Only 7 cards total across the two groups on the real page — the
    owner's own Q3 answer ("Deux blocs dépliés par défaut") over the
    Time Machine ribbon's own default-open-but-collapsible-at-scale
    precedent, which exists for dozens of streams, not 7 cards.
    """

    document = render_html((selection_ui_link(), health_link()))

    assert '<details class="link-group link-group-lan" open>' in document
    assert '<details class="link-group link-group-public" open>' in document


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


def test_a_domain_with_findings_links_to_its_health_html_anchor():
    """
    Added 2026-09-30 — the owner, reading this exact badge: "les
    findings en rouge doivent être cliquables". `domain_slug` (shared
    with `aistack.renderers.health.html`'s own `id="domain-<slug>"`)
    is what the two renderers agree on without sharing code.
    """

    cockpit = HealthCockpit(
        domains=(
            HealthDomain(
                name="Tests PRA", instrumented=True, findings=(_dummy_finding(),)
            ),
        )
    )

    document = render_html((selection_ui_link(),), cockpit=cockpit)

    assert '<a class="domain-badge badge-alert" href="/health.html#domain-tests-pra" title=' in document


def test_a_clean_domain_is_not_a_link():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True, findings=()),))

    document = render_html((selection_ui_link(),), cockpit=cockpit)

    assert "<a" not in document.split('class="cartouche-badges"')[1].split("</div>")[0]


def test_a_not_instrumented_domain_is_not_a_link():
    cockpit = HealthCockpit(
        domains=(HealthDomain(name="Services", instrumented=False, note="pas encore"),)
    )

    document = render_html((selection_ui_link(),), cockpit=cockpit)

    assert "<a" not in document.split('class="cartouche-badges"')[1].split("</div>")[0]


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


# --------------------------------------------------------------------
# Localization (ADR-0010, 2026-09-27)
# --------------------------------------------------------------------


def _cockpit() -> HealthCockpit:
    return HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True, findings=()),
            HealthDomain(name="Services", instrumented=False, note="pas encore"),
            HealthDomain(name="Tests PRA", instrumented=True, findings=(_dummy_finding(),)),
        )
    )


def test_the_reference_language_is_served_when_none_is_asked_for():
    document = render_html((selection_ui_link(),), cockpit=_cockpit())

    assert '<html lang="fr">' in document
    assert "État de santé du homelab" in document


def test_the_page_is_written_in_the_requested_language():
    score = HealthScore(value=72, measured_domains=2, total_domains=3, bucket=TO_WATCH)

    document = render_html(
        (selection_ui_link(),), cockpit=_cockpit(), score=score, lang="en"
    )

    assert '<html lang="en">' in document
    assert "Homelab health" in document
    assert "Health score:" in document
    assert "to watch" in document
    assert "Storage — nothing to report" in document
    assert "Services — not instrumented" in document
    assert "DR tests — 1 finding(s)" in document
    assert "See the detail by domain" in document
    assert "État de santé" not in document


def test_what_the_page_displays_is_not_translated():
    """ADR-0010 § 4: a declared note stays in the language it was written in."""

    document = render_html(
        (selection_ui_link(),), cockpit=_cockpit(), score_note="poids absents", lang="en"
    )

    assert "Health score: not computed — poids absents" in document


def test_an_absolute_link_carries_the_page_language():
    document = render_html((selection_ui_link(), health_link()), lang="en")

    assert 'href="http://GIGABYTE:8181?lang=en"' in document
    assert 'href="/health.html"' in document


def test_every_page_offers_settings_and_every_declared_language():
    document = render_html((selection_ui_link(),), lang="en")

    assert 'href="/settings"' in document
    assert ">Settings<" in document
    assert 'href="?lang=fr"' in document
    # Each language by its flag, its own name kept as alt text and
    # tooltip (owner's request, 2026-09-27).
    assert 'title="Français"' in document
    assert 'alt="Français"' in document
    assert 'title="English" aria-current="true"><img class="flag"' in document
    assert 'src="data:image/svg+xml;base64,' in document
    # The console is where the way back leads; it offers none itself.
    assert 'class="console-link"' not in document


def test_an_unknown_language_is_served_in_the_reference():
    document = render_html((selection_ui_link(),), lang="xx")

    assert '<html lang="fr">' in document


def test_the_group_marker_reaches_the_page_as_a_css_escape():
    # Python read "\25B8" as the octal escape \x15 followed by "B8":
    # the browser drew an unknown-character box in front of each
    # group title (seen on GIGABYTE, 2026-10-08).
    document = render_html((selection_ui_link(),))

    assert 'content: "\\25B8"' in document
    assert not any(ord(character) < 32 and character not in "\n\t" for character in document)


def test_a_lan_card_ends_with_its_scope_in_italics_on_its_own_line():
    document = render_html((selection_ui_link(),))

    card = document.split('class="card card-lan"', 1)[1].split("</a>", 1)[0]
    assert card.rstrip().endswith('<p class="card-scope"><em>Accessible uniquement depuis le réseau local.</em></p>')
    assert card.count("Accessible uniquement depuis le réseau local") == 1


def test_a_description_written_before_still_shows_the_scope_once():
    old = ConsoleLink(
        name="Selection UI",
        description="Choisir les morceaux. Accessible uniquement depuis le\n réseau local.",
        url="http://GIGABYTE:8181",
        scope=LAN,
    )
    english = ConsoleLink(
        name="Time Machine",
        description="AIStack's complete history — AIStack web application, LAN listener only (ADR-0012)",
        url="http://GIGABYTE:8181",
        scope=LAN,
    )

    document = render_html((old, english))

    assert document.count("Accessible uniquement depuis le réseau local") == 2
    assert "<p>Choisir les morceaux.</p>" in document
    assert "LAN listener" not in document


def test_a_public_card_says_no_scope_line():
    assert 'class="card-scope"' not in render_html((health_link(),))


def test_a_card_whose_screen_uses_ai_says_so_under_an_ai_mark():
    assistant = ConsoleLink(
        name="Assistant de pannes",
        description="Diagnostiquer une panne réelle.",
        url="http://GIGABYTE:8186/troubleshooting/",
        scope=LAN,
        ai="Un modèle d'IA local raisonne sur la panne.",
    )

    document = render_html((assistant, selection_ui_link()))

    card = document.split("Assistant de pannes", 1)[1].split("</a>", 1)[0]
    assert '<span class="ai-mark"' in card and ">IA</span> Un modèle d'IA local" in card
    # Before the scope line, which stays last.
    assert card.index("card-ai") < card.index("card-scope")
    assert document.count('class="card-ai"') == 1


def test_the_shipped_cards_mark_the_screens_that_use_ai():
    from pathlib import Path

    import aistack
    from aistack.console.yaml import load_console_links_yaml

    shipped = Path(aistack.__file__).parent / "console" / "definitions" / "console_links.yml"
    links = load_console_links_yaml(shipped, lang="fr")

    assert sorted(link.name for link in links if link.ai) == ["Assistant de pannes", "Cockpit Santé", "Time Machine"]


def test_the_running_version_sits_under_the_lockup() -> None:
    # The owner, 2026-10-09: "mettre le numéro de version en cours sous
    # le logo AIStack sur la page console".
    page = render_html((), version="1.11.0", lang="fr")
    lockup = page.index('class="lockup"')
    line = page.index('<p class="aside-version">Version 1.11.0</p>')
    assert lockup < line < page.index('class="aside-intro"')


def test_no_version_line_when_the_version_is_unknown() -> None:
    assert "aside-version\">" not in render_html((), version="unknown")
    assert "aside-version\">" not in render_html(())


def test_no_shipped_card_shows_a_plan_reference_in_english() -> None:
    # The English console still said "(PLAN-J2)", "(PLAN-J7)" on the
    # internet cards (screenshot, 2026-10-09).
    from pathlib import Path

    import aistack
    from aistack.console.yaml import load_console_links_yaml

    shipped = Path(aistack.__file__).parent / "console" / "definitions" / "console_links.yml"
    for lang in ("fr", "en"):
        for link in load_console_links_yaml(shipped, lang=lang):
            assert "PLAN-" not in link.description, (lang, link.name)
