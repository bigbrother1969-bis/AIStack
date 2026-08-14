#!/usr/bin/env python3

from pathlib import Path
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


# Where the projection is written.
#
# Overridable so that a test or a CI job never overwrites the
# published projection of the repository it runs in.
BUNDLE_OUTPUT_DIR = Path(
    os.getenv(
        "AISTACK_BUNDLE_OUTPUT_DIR",
        str(ROOT / "context" / "bundles"),
    )
)


OUTPUT = (
    BUNDLE_OUTPUT_DIR
    / "AIStack-Context-Bundle.zip"
)


README_OUTPUT = (
    BUNDLE_OUTPUT_DIR
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


def repository_url() -> str:
    """
    Canonical location of the governance SPOT.

    AISTACK_REPOSITORY_URL should be set to the public
    canonical URL. The git remote is only a fallback and
    may expose an internal address, which must never be
    published inside a mirrored bundle.
    """

    override = os.getenv(
        "AISTACK_REPOSITORY_URL",
    )

    if override:
        return override.strip()

    try:
        return subprocess.check_output(
            [
                "git",
                "remote",
                "get-url",
                "origin",
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


    # The service owns bundle transport and already
    # transfers OUTPUT. Only the companion README has to
    # be transferred here.
    bundle = service.generate(
        source_path=ROOT,
        output_path=OUTPUT,
        source_commit=git_commit(),
        repository_url=repository_url(),
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
        f"- Repository: {bundle.repository_url}"
    )

    print(
        f"- Output: {OUTPUT}"
    )


    delivery_failed = False


    if transfer_service:

        error = service.transfer_error

        if error is None:

            try:
                transfer_service.transfer(
                    README_OUTPUT,
                )

            except Exception as readme_error:
                error = readme_error


        if error is None:

            print(
                "- Transferred to configured target"
            )

        else:

            delivery_failed = True

            print(
                f"- Delivery FAILED: {error}"
            )


    if delivery_failed:

        print(
            "Bundle generated and valid. "
            "Delivery did not complete."
        )

        sys.exit(2)


if __name__ == "__main__":
    main()
