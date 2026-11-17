import os
import subprocess
import sys
from pathlib import Path


def test_legacy_export_script_generates_bundle(tmp_path):
    """
    The official export script runs over the real repository and
    writes the projection where it is told to.

    The output directory is given through the environment: a test
    must never write into the repository it runs in (the script
    documents `AISTACK_BUNDLE_OUTPUT_DIR` for that reason).
    """

    root = Path(__file__).parents[4]

    script = root / "scripts" / "export_project_sources.py"

    assert script.exists()

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "AISTACK_BUNDLE_OUTPUT_DIR": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr

    assert (tmp_path / "AIStack-Context-Bundle.zip").exists()

    assert (tmp_path / "README.md").exists()

    assert not (root / "context").exists()
