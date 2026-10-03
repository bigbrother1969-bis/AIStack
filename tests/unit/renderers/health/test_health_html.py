from __future__ import annotations

from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH, HealthScore
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.technical_debt_score import (
    TECHNICAL_DEBT_QUALIFICATION,
    TechnicalDebtScore,
)
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.renderers.health.html import render_html


def storage_finding(mount: str = "/") -> RuntimeFinding:
    return RuntimeFinding(
        subject=mount,
        signature="OPS-0004",
        interpretation="Free space fell below the declared threshold.",
        remediation="Free some space or raise the threshold.",
        confidence="Measured",
        grounding="unknown",
        evidence=(
            CitedReading(
                provider="aistack.provider.storage",
                reading=StorageReading(
                    mount=mount, total_bytes=100, used_bytes=99, free_bytes=1
                ),
            ),
        ),
        qualifications=("OPS-0004/deployment-misconfiguration",),
    )


# --------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------


def test_the_document_is_a_self_contained_html_page():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(cockpit)

    assert document.startswith("<!doctype html>")
    assert "<title>AIStack — Cockpit Santé</title>" in document
    assert document.strip().endswith("</html>")


def test_the_page_declares_a_viewport():
    """
    Added 2026-09-30
    (`claude/AUDIT-CONSOLE-ARCHITECTURE-HEALTH-2026-09-29.md`, constat
    1) — this page had none, unlike Time Machine's own screens.
    """

    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(cockpit)

    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in document


def test_the_mark_is_embedded_as_the_favicon():
    """
    Added 2026-09-30
    (`claude/AUDIT-CONSOLE-ARCHITECTURE-HEALTH-2026-09-29.md`, constat
    3) — only `console.html` had one before; this page reuses the same
    vendored mark (`aistack.renderers.assets.MARK_DATA_URI`).
    """

    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(cockpit)

    assert '<link rel="icon" href="data:image/png;base64,' in document


def test_the_meta_line_counts_instrumented_domains():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True),
            HealthDomain(name="Services", instrumented=False, note="pas encore"),
        )
    )

    document = render_html(cockpit)

    assert "1 / 2 domaine(s) instrumenté(s)" in document


def test_rendering_the_same_cockpit_twice_is_byte_identical():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True, findings=(storage_finding(),)),
            HealthDomain(name="Services", instrumented=False, note="pas encore"),
        )
    )

    assert render_html(cockpit) == render_html(cockpit)


# --------------------------------------------------------------------
# A not-instrumented domain: named, never displayed as healthy
# --------------------------------------------------------------------


def test_a_not_instrumented_domain_shows_its_own_note_not_a_clean_badge():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(
                name="GPU",
                instrumented=False,
                note="aucun cas réel cité pour ce domaine",
            ),
        )
    )

    document = render_html(cockpit)

    assert "non instrumenté" in document
    assert "aucun cas réel cité pour ce domaine" in document
    assert "rien à signaler" not in document


# --------------------------------------------------------------------
# An instrumented domain with nothing to report
# --------------------------------------------------------------------


def test_an_instrumented_domain_with_no_findings_reads_as_clean():
    cockpit = HealthCockpit(
        domains=(HealthDomain(name="Stockage", instrumented=True, findings=()),)
    )

    document = render_html(cockpit)

    assert "rien à signaler" in document
    assert "non instrumenté" not in document


# --------------------------------------------------------------------
# An instrumented domain with findings
# --------------------------------------------------------------------


def test_an_instrumented_domain_with_findings_lists_each_one():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(
                name="Stockage",
                instrumented=True,
                findings=(storage_finding("/"), storage_finding("/media/Films")),
            ),
        )
    )

    document = render_html(cockpit)

    assert "2 finding(s)" in document
    assert "/media/Films" in document
    assert "OPS-0004" in document
    assert "OPS-0004/deployment-misconfiguration" in document
    assert "Free some space or raise the threshold." in document


def test_the_evidence_count_and_provider_are_shown():
    cockpit = HealthCockpit(
        domains=(HealthDomain(name="Stockage", instrumented=True, findings=(storage_finding(),)),)
    )

    document = render_html(cockpit)

    assert "1 lecture(s) citée(s)" in document
    assert "aistack.provider.storage" in document


# --------------------------------------------------------------------
# Escaping
# --------------------------------------------------------------------


def test_a_domains_note_is_html_escaped():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(
                name="Services",
                instrumented=False,
                note="<script>alert(1)</script>",
            ),
        )
    )

    document = render_html(cockpit)

    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;" in document


def test_a_findings_interpretation_is_html_escaped():
    finding = RuntimeFinding(
        subject="/",
        signature="OPS-0004",
        interpretation="<b>free space</b> & more",
        remediation="ok",
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
    cockpit = HealthCockpit(
        domains=(HealthDomain(name="Stockage", instrumented=True, findings=(finding,)),)
    )

    document = render_html(cockpit)

    assert "<b>free space</b>" not in document
    assert "&lt;b&gt;free space&lt;/b&gt; &amp; more" in document


# --------------------------------------------------------------------
# Score (OPS-0008) — optional, backward compatible
# --------------------------------------------------------------------


def test_no_score_and_no_note_renders_no_score_section():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(cockpit)

    assert "Score de santé" not in document


def test_a_computed_score_is_shown_with_its_bucket():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = HealthScore(value=82, measured_domains=3, total_domains=4, bucket=TO_WATCH)

    document = render_html(cockpit, score=score)

    assert "Score de santé" in document
    assert "82/100" in document
    assert "à surveiller" in document
    assert "3/4 domaine(s) mesuré(s)" in document
    assert "badge-watch" in document


def test_an_excellent_score_uses_the_clean_badge():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = HealthScore(value=100, measured_domains=4, total_domains=4, bucket=EXCELLENT)

    document = render_html(cockpit, score=score)

    assert "badge-clean" in document


def test_an_action_required_score_uses_the_alert_badge():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = HealthScore(value=40, measured_domains=4, total_domains=4, bucket=ACTION_REQUIRED)

    document = render_html(cockpit, score=score)

    assert "badge-alert" in document


def test_a_score_note_is_shown_when_the_score_could_not_be_computed():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(
        cockpit, score=None, score_note="no health-score weight definition at ..."
    )

    assert "Score de santé : non calculé" in document
    assert "no health-score weight definition" in document


def test_a_score_note_is_html_escaped():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(cockpit, score=None, score_note="<script>bad()</script>")

    assert "<script>bad()</script>" not in document
    assert "&lt;script&gt;" in document


# --------------------------------------------------------------------
# Dette technique (PLAN-J11 § 11.9.1) — optional, backward compatible
# --------------------------------------------------------------------


def debt_finding() -> RuntimeFinding:
    return RuntimeFinding(
        subject="gluetun",
        signature="OPS-0004",
        interpretation="restarting",
        remediation="investigate boot order",
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
        qualifications=(TECHNICAL_DEBT_QUALIFICATION,),
    )


def test_no_technical_debt_score_and_no_note_renders_no_card():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(cockpit)

    assert "Dette technique" not in document


def test_a_computed_technical_debt_score_is_shown_with_its_bucket():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = TechnicalDebtScore(value=85, findings=(debt_finding(),), bucket=TO_WATCH)

    document = render_html(cockpit, technical_debt_score=score)

    assert "Dette technique" in document
    assert "85/100" in document
    assert "à surveiller" in document
    assert "1 finding(s)" in document
    assert "badge-watch" in document


def test_an_excellent_technical_debt_score_uses_the_clean_badge():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = TechnicalDebtScore(value=100, findings=(), bucket=EXCELLENT)

    document = render_html(cockpit, technical_debt_score=score)

    assert "badge-clean" in document


def test_an_action_required_technical_debt_score_uses_the_alert_badge():
    findings = tuple(
        RuntimeFinding(
            subject=str(i),
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
            qualifications=(TECHNICAL_DEBT_QUALIFICATION,),
        )
        for i in range(10)
    )
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = TechnicalDebtScore(value=0, findings=findings, bucket=ACTION_REQUIRED)

    document = render_html(cockpit, technical_debt_score=score)

    assert "badge-alert" in document


def test_a_technical_debt_note_is_shown_when_the_score_could_not_be_computed():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(
        cockpit,
        technical_debt_score=None,
        technical_debt_note="no health-score weight definition available; "
        "technical-debt score is not computed",
    )

    assert "Dette technique : non calculée" in document
    assert "no health-score weight definition" in document


def test_a_technical_debt_note_is_html_escaped():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))

    document = render_html(
        cockpit, technical_debt_score=None, technical_debt_note="<script>bad()</script>"
    )

    assert "<script>bad()</script>" not in document
    assert "&lt;script&gt;" in document


def test_the_technical_debt_card_appears_right_after_the_global_score():
    """
    The owner's own declared placement, 2026-09-23: "juste après le
    score santé global" — this checks it, not just that both render
    somewhere on the page.
    """

    cockpit = HealthCockpit(domains=(HealthDomain(name="Stockage", instrumented=True),))
    score = HealthScore(value=82, measured_domains=3, total_domains=4, bucket=TO_WATCH)
    debt_score = TechnicalDebtScore(value=100, findings=(), bucket=EXCELLENT)

    document = render_html(cockpit, score=score, technical_debt_score=debt_score)

    assert document.index("Score de santé") < document.index("Dette technique")


# --------------------------------------------------------------------
# Localization (ADR-0010, 2026-09-27)
# --------------------------------------------------------------------


def test_the_cockpit_is_written_in_the_requested_language():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True, findings=()),
            HealthDomain(name="Sauvegarde / PRA", instrumented=False, note="aucun seuil déclaré"),
        )
    )
    score = HealthScore(value=82, measured_domains=1, total_domains=2, bucket=TO_WATCH)

    document = render_html(cockpit, score=score, lang="en")

    assert '<html lang="en">' in document
    assert "<title>AIStack — Health cockpit</title>" in document
    assert "1 / 2 domain(s) instrumented" in document
    assert "Health score:" in document
    assert "to watch" in document
    assert "1/2 domain(s) measured" in document
    assert "Storage <span" in document
    assert "nothing to report" in document
    assert "Backup / DR <span" in document
    assert "not instrumented" in document
    # ADR-0010 § 4: a declared note is shown as it was written.
    assert "aucun seuil déclaré" in document


def test_the_reference_page_carries_the_navigation_strip():
    document = render_html(HealthCockpit(domains=()))

    assert '<html lang="fr">' in document
    assert 'href="/settings"' in document
    assert 'href="?lang=en"' in document
    assert 'href="/console.html?lang=fr" title="Revenir à la console' in document
    assert '>← Retour à la console<' in document


# --------------------------------------------------------------------
# Domain anchors and the troubleshooting-assistant link (2026-09-30)
# --------------------------------------------------------------------


def test_every_domain_section_carries_an_anchor_id_whatever_its_state():
    """
    `console.html`'s own domain pills (`aistack.renderers.console.html`)
    link to `health.html#domain-<slug>` — every domain section needs
    the matching `id`, not only the ones currently in alert, so a pill
    keeps working if a domain's state changes between the two renders.
    """

    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True, findings=(storage_finding(),)),
            HealthDomain(name="Services", instrumented=True, findings=()),
            HealthDomain(name="GPU", instrumented=False, note="aucun capteur"),
        )
    )

    document = render_html(cockpit)

    assert 'id="domain-stockage"' in document
    assert 'id="domain-services"' in document
    assert 'id="domain-gpu"' in document


def test_no_diagnose_button_when_troubleshooting_base_url_is_absent():
    """
    `None` (every call before this feature existed) renders exactly as
    before — the same idiom `score`/`technical_debt_score` already
    hold for their own optional parameters.
    """

    cockpit = HealthCockpit(
        domains=(HealthDomain(name="Stockage", instrumented=True, findings=(storage_finding(),)),)
    )

    document = render_html(cockpit)

    # The `.diagnose` CSS rule ships unconditionally (a handful of
    # harmless, unused bytes) — what must be absent is the button
    # itself and any actual submission target.
    assert "<form" not in document
    assert "/finding/" not in document


def test_diagnose_button_links_to_the_troubleshooting_assistant_by_bare_subject():
    cockpit = HealthCockpit(
        domains=(HealthDomain(name="Stockage", instrumented=True, findings=(storage_finding("/data"),)),)
    )

    document = render_html(cockpit, troubleshooting_base_url="http://GIGABYTE:8185")

    # A link to the finding on the Troubleshooting screen, never a form
    # posting across sites (ADR-0014 § 3); the key is encoded whole.
    assert 'class="diagnose" href="http://GIGABYTE:8185/#finding-%2Fdata"' in document
    assert "<form" not in document


def test_diagnose_button_uses_a_domain_qualified_key_on_a_real_subject_collision():
    """
    The same collision `troubleshooting_assistant_ui.app.QualifiedFinding`
    guards against — two different domains naming the same subject —
    confirmed real for "gigabyte"/"nextcloud"/"immich" across Tests PRA
    and État persistant, 2026-09-30. This renderer must route each to
    a distinct key, never silently pick one.
    """

    def finding(subject: str, signature: str) -> RuntimeFinding:
        return RuntimeFinding(
            subject=subject,
            signature=signature,
            interpretation="synthetic",
            remediation="synthetic",
            confidence="Measured",
            grounding="unknown",
            evidence=(CitedReading(provider="synthetic", reading="synthetic"),),
            qualifications=(),
        )

    cockpit = HealthCockpit(
        domains=(
            HealthDomain(
                name="Tests PRA", instrumented=True, findings=(finding("gigabyte", "OPS-0009"),)
            ),
            HealthDomain(
                name="État persistant",
                instrumented=True,
                findings=(finding("gigabyte", "OPS-0010"),),
            ),
        )
    )

    document = render_html(cockpit, troubleshooting_base_url="http://GIGABYTE:8185")

    assert "http://GIGABYTE:8185/#finding-Tests%20PRA%3A%3Agigabyte" in document
    assert "http://GIGABYTE:8185/#finding-%C3%89tat%20persistant%3A%3Agigabyte" in document
    # Never the bare, ambiguous subject on its own.
    assert '#finding-gigabyte"' not in document


def test_diagnose_button_keeps_the_bare_subject_when_it_is_unique():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(
                name="Tests PRA",
                instrumented=True,
                findings=(
                    RuntimeFinding(
                        subject="raspberry",
                        signature="OPS-0009",
                        interpretation="synthetic",
                        remediation="synthetic",
                        confidence="Measured",
                        grounding="unknown",
                        evidence=(CitedReading(provider="synthetic", reading="synthetic"),),
                        qualifications=(),
                    ),
                ),
            ),
        )
    )

    document = render_html(cockpit, troubleshooting_base_url="http://GIGABYTE:8185")

    assert "http://GIGABYTE:8185/#finding-raspberry\"" in document


# --------------------------------------------------------------------
# A finding speaks the page's language (ADR-0010 § 4, revised 2026-10-03)
# --------------------------------------------------------------------


def test_an_evaluator_s_finding_is_shown_in_the_page_s_language():
    from aistack.contracts.backup_gap import MISSING, BackupGap
    from aistack.contracts.backup_reading import BackupReading
    from aistack.runtime.evaluate_backup import evaluate_backup
    from datetime import datetime, timezone

    gap = BackupGap(
        reading=BackupReading(
            path="/media/BACKUP/SQL_BACKUPS/nextcloud",
            observed_at=datetime.now(timezone.utc),
            newest_file_mtime=None,
        ),
        max_age_hours=36.0,
        reason=MISSING,
    )
    (finding,) = evaluate_backup([gap])
    cockpit = HealthCockpit(
        domains=(HealthDomain(name="Sauvegarde / PRA", instrumented=True, findings=(finding,)),)
    )

    french = render_html(cockpit, lang="fr")
    english = render_html(cockpit, lang="en")

    assert "ne contient aucun fichier de sauvegarde" in french
    assert "Mesuré" in french
    assert "holds no backup file at all" not in french
    assert "holds no backup file at all" in english
