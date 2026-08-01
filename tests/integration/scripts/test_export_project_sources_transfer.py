from pathlib import Path
import os
import subprocess
import sys

def test_export_project_sources_generates_bundle():

    root = Path(__file__).parents[3]

    script = (
        root
        / "scripts"
        / "export_project_sources.py"
    )

    assert script.exists()


    result = subprocess.run(
        [
            sys.executable,
            str(script),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "AISTACK_DISABLE_TRANSFER": "true",
        },
    )


    assert result.returncode == 0, result.stderr


    bundle = (
        root
        / "context"
        / "bundles"
        / "AIStack-Context-Bundle.zip"
    )

    assert bundle.exists()
