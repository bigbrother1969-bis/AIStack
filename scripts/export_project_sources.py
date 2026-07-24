#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

OUTPUT = (
    ROOT
    / "context"
    / "bundles"
    / "AIStack-Context-Bundle.zip"
)


def git_commit() -> str:
    try:
        return subprocess.check_output(
            [
                "git",
                "rev-parse",
                "--short",
                "HEAD",
            ],
            cwd=ROOT,
            text=True,
        ).strip()

    except Exception:
        return "unknown"


def main() -> None:

    # Allow execution without package installation
    sys.path.insert(
        0,
        str(ROOT / "src"),
    )

    from aistack.context_bundle.service import (
        DefaultContextBundleService,
    )


    service = (
        DefaultContextBundleService()
    )


    bundle = service.generate(
        source_path=ROOT,
        output_path=OUTPUT,
        source_commit=git_commit(),
    )


    print(
        "Generated Context Bundle:"
    )

    print(
        f"- ID: {bundle.id}"
    )

    print(
        f"- Artifacts: {len(bundle.artifacts)}"
    )

    print(
        f"- Output: {OUTPUT}"
    )


if __name__ == "__main__":
    main()
