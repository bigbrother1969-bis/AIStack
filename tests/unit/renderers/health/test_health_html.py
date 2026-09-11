from __future__ import annotations

from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.storage_reading import StorageReading
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
