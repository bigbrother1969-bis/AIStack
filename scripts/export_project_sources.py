#!/usr/bin/env python3

from pathlib import Path
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


OUTPUT = (
    ROOT
    / "context"
    / "bundles"
    / "AIStack-Context-Bundle.zip"
)


README_OUTPUT = (
    ROOT
    / "context"
    / "bundles"
    / "README.md"
)


TRANSFER_CONFIG = (
    ROOT
    / "config"
    / "context_bundle_transfer.yml"
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

    sys.path.insert(
        0,
        str(ROOT / "src"),
    )


    from aistack.context_bundle.service import (
        DefaultContextBundleService,
    )

    from aistack.context_bundle.export.readme_bundle_exporter import (
        ReadmeBundleExporter,
    )

    from aistack.context_bundle.transfer.config_loader import (
        load_transfer_configuration,
    )

    from aistack.context_bundle.transfer.ssh_bundle_transfer import (
        SshBundleTransfer,
    )


    transfer_service = None


    transfer_disabled = (
        os.getenv(
            "AISTACK_DISABLE_TRANSFER",
            "false",
        ).lower()
        == "true"
    )


    if (
        TRANSFER_CONFIG.exists()
        and not transfer_disabled
    ):

        configuration = load_transfer_configuration(
            TRANSFER_CONFIG
        )

        if configuration.enabled:

            transfer_service = SshBundleTransfer(
                config=configuration,
            )


    service = DefaultContextBundleService(
        transfer_service=transfer_service,
    )


    bundle = service.generate(
        source_path=ROOT,
        output_path=OUTPUT,
        source_commit=git_commit(),
    )


    README_OUTPUT.write_text(
        ReadmeBundleExporter().export(),
        encoding="utf-8",
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


    if transfer_service:

        transfer_service.transfer(
            OUTPUT,
        )

        transfer_service.transfer(
            README_OUTPUT,
        )

        print(
            "- Transferred to laptop"
        )


if __name__ == "__main__":
    main()
