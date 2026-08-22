from pathlib import Path
import os
import subprocess
import sys

import pytest


ROOT = Path(__file__).parents[3]


@pytest.fixture(scope="module")
def integrity_report(tmp_path_factory) -> subprocess.CompletedProcess:
    """
    The projection of this repository, regenerated and validated.

    The bundle is written under a temporary directory.
    `AISTACK_BUNDLE_OUTPUT_DIR` exists for this: STD-0002 forbids
    a test from producing an operational artifact, and the
    published projection of the repository under test is never
    overwritten.

    Generated once for the module — the two criteria below read
    the same run, as a single execution of the validator produces
    both facts.
    """

    output = tmp_path_factory.mktemp("projection")

    export = ROOT / "scripts" / "export_project_sources.py"

    assert export.exists()

    generated = subprocess.run(
        [sys.executable, str(export)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": "src",
            "AISTACK_DISABLE_TRANSFER": "true",
            "AISTACK_BUNDLE_OUTPUT_DIR": str(output),
        },
    )

    assert generated.returncode == 0, generated.stderr

    bundle = output / "AIStack-Context-Bundle.zip"

    assert bundle.exists(), generated.stdout

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "aistack.cli.knowledge_integrity",
            str(bundle),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )


def test_criterion_2_5_the_validator_exits_zero_on_the_projection(
    integrity_report,
):
    """
    STD-0300 § VS-2 criterion 2.5, executed.

    *`aistack.cli.knowledge_integrity` exits 0 on the bundle
    used.* The criterion makes the validation suite
    self-checking: it fails while the heritage the suite
    transmits is itself unsound.

    It was recorded as **failing** from 2026-08-14, on a blocking
    finding of `criticality-discrimination` — *no artifact is
    declared C3*. Artifacts declaring C3 have existed since
    2026-07-24, three weeks before the note was written. The
    criterion spent eight days asserting a failure whose cause
    had already gone, and nothing distinguished that from a live
    one, because **no test ever ran the validator on the real
    projection**. The two tests that existed built synthetic
    bundles in `tmp_path`; a regression in the governed heritage
    left the suite green.

    This test is the criterion itself, so a regression is visible
    per commit — what § 11 asks of any criterion that becomes
    automated. Mutation-tested by downgrading the fifteen C3
    artifacts to C2, which reproduces the 2026-08-14 finding
    exactly and fails this test.

    The report is the failure message. A bare exit code would say
    the heritage is unsound without saying how.
    """

    assert integrity_report.returncode == 0, integrity_report.stdout

    assert "blocking: 0" in integrity_report.stdout


def test_criterion_2_6_the_report_declares_the_heritage_clean(
    integrity_report,
):
    """
    STD-0300 § VS-2 criterion 2.6, executed.

    2.5 covers blocking findings only, and the validator exits 0
    with warnings. Measured 2026-08-22: removing `owner` from one
    governed artifact produces `warnings: 1  clean: False` and an
    exit code of 0 — the suite passes while the heritage it
    transmits has degraded. The `clean` field already carried
    that fact and nothing read it.

    2.6 was added rather than folding the requirement into 2.5,
    so that *degraded* and *broken* keep different weights: a
    missing metadata field should not carry the gravity of a
    heritage with no minimal governed context.
    """

    assert "clean: True" in integrity_report.stdout
