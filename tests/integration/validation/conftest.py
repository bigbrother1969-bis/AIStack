from pathlib import Path
import os
import subprocess
import sys

import pytest

from aistack.contracts.context_bundle import ContextBundle
from aistack.integrity.bundle_reader import read_bundle


ROOT = Path(__file__).parents[3]


@pytest.fixture(scope="session")
def projection(tmp_path_factory) -> ContextBundle:
    """
    The projection of this repository, regenerated here.

    **Regenerated, never read from `context/bundles/`.** A first
    version of the reference test read the published archive — a
    generated, unversioned file — and it failed on the owner's
    machine while passing on the agent's, at the same commit: the
    archive there predated the change it was meant to verify. A
    test whose result depends on the order of the last three
    commands is not a test.

    Session-scoped because the export walks the whole heritage,
    and every check that asks a question about the real artifacts
    should ask it of one projection rather than of one each.

    STD-0002: the archive is written under `tmp_path_factory`,
    never over the published projection.
    """

    directory = tmp_path_factory.mktemp("projection")

    generated = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "export_project_sources.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": "src",
            "AISTACK_DISABLE_TRANSFER": "true",
            "AISTACK_BUNDLE_OUTPUT_DIR": str(directory),
        },
    )

    assert generated.returncode == 0, generated.stderr

    archive = directory / "AIStack-Context-Bundle.zip"

    assert archive.exists(), generated.stdout

    return read_bundle(archive)
