from pathlib import Path
import subprocess


def test_legacy_export_script_generates_bundle():

    root = Path(__file__).parents[4]

    script = (
        root
        / "scripts"
        / "export_project_sources.py"
    )

    assert script.exists()


    result = subprocess.run(
        [
            "python",
            str(script),
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )


    assert result.returncode == 0


    bundle_dir = (
        root
        / "context"
        / "bundles"
    )


    assert (
        bundle_dir
        / "AIStack-Context-Bundle.zip"
    ).exists()

    assert (
        bundle_dir
        / "README.md"
    ).exists()
