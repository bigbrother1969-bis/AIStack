from pathlib import Path
import json
import os
import subprocess
import sys
import zipfile


def test_export_project_sources_generates_bundle(tmp_path):
    """
    The suite must never overwrite the published projection of
    the repository it runs in. The bundle is generated into a
    temporary location.
    """

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
            "AISTACK_BUNDLE_OUTPUT_DIR": str(tmp_path),
        },
    )


    assert result.returncode == 0, result.stderr


    bundle = tmp_path / "AIStack-Context-Bundle.zip"

    assert bundle.exists()


def test_export_does_not_touch_the_published_bundle(tmp_path):
    """
    Guard against the regression itself: running the export
    into a temporary directory must leave the repository's own
    projection untouched.
    """

    root = Path(__file__).parents[3]

    published = (
        root
        / "context"
        / "bundles"
        / "AIStack-Context-Bundle.zip"
    )

    before = (
        published.stat().st_mtime_ns
        if published.exists()
        else None
    )


    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "export_project_sources.py"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "AISTACK_DISABLE_TRANSFER": "true",
            "AISTACK_BUNDLE_OUTPUT_DIR": str(tmp_path),
        },
        check=True,
    )


    after = (
        published.stat().st_mtime_ns
        if published.exists()
        else None
    )

    assert after == before


def test_generated_bundle_carries_its_manifest(tmp_path):

    root = Path(__file__).parents[3]

    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "export_project_sources.py"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "AISTACK_DISABLE_TRANSFER": "true",
            "AISTACK_BUNDLE_OUTPUT_DIR": str(tmp_path),
        },
        check=True,
    )

    with zipfile.ZipFile(
        tmp_path / "AIStack-Context-Bundle.zip"
    ) as archive:

        manifest = json.loads(
            archive.read("manifest.json")
        )

    assert manifest["hash_algorithm"] == "sha256"
    assert len(manifest["content_hash"]) == 64
