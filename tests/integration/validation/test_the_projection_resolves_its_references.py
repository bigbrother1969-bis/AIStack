from pathlib import Path
import os
import subprocess
import sys

from aistack.integrity.bundle_reader import read_bundle
from aistack.integrity.checks.reference_integrity import (
    ReferenceIntegrityCheck,
)


ROOT = Path(__file__).parents[3]


def test_the_published_heritage_resolves_every_reference(tmp_path):
    """
    Every `relations: references:` in this repository designates
    an artifact this repository declares.

    **The projection is regenerated here, and that is the point.**
    A first version of this test read
    `context/bundles/AIStack-Context-Bundle.zip` — a generated,
    unversioned file — and it failed on the owner's machine while
    passing on the agent's, at the same commit. The archive there
    predated the change it was meant to verify. A test whose
    result depends on the order of the last three commands is not
    a test.

    Worse, it carried `if not projection.exists(): return`, so on
    a fresh clone it passed while verifying nothing. Both defects
    were introduced on 2026-08-23 in the test file of the check
    written to catch exactly this shape of declaration.

    STD-0002: the archive is written to `tmp_path`, never over the
    published projection.
    """

    generated = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "export_project_sources.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": "src",
            "AISTACK_DISABLE_TRANSFER": "true",
            "AISTACK_BUNDLE_OUTPUT_DIR": str(tmp_path),
        },
    )

    assert generated.returncode == 0, generated.stderr

    bundle = tmp_path / "AIStack-Context-Bundle.zip"

    assert bundle.exists(), generated.stdout

    findings = ReferenceIntegrityCheck().evaluate(read_bundle(bundle))

    assert findings == [], [f.subjects for f in findings]
