#!/usr/bin/env python3

from pathlib import Path
import ipaddress
import os
import re
import subprocess
import tomllib
from urllib.parse import urlparse
import sys


ROOT = Path(__file__).resolve().parents[1]


LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
HOSTNAME = re.compile(rf"{LABEL}(?:\.{LABEL})+")


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


def is_publishable_url(url: str) -> bool:
    """
    True when a URL can mean something to a reader elsewhere.

    A loopback address, a private range or a bare hostname is
    canonical for nobody: it describes the machine that ran the
    export, not where AIStack lives.
    """

    host = urlparse(url).hostname

    if not host:
        # scp-style remote, "git@host:path"
        head = url.split(":", 1)[0]
        host = head.rsplit("@", 1)[-1] or None

    if not host:
        return False

    if host == "localhost" or host.endswith(".local"):
        return False

    try:
        return not ipaddress.ip_address(host).is_private

    except ValueError:
        pass

    # A hostname a reader elsewhere can resolve: at least two
    # labels. A bare name resolves only inside the network that
    # produced it, which is the defect this function exists for.
    return bool(HOSTNAME.fullmatch(host))


def declared_repository_url() -> str | None:
    """
    The canonical URL the project declares about itself.

    `pyproject.toml` is where a Python project states its own
    location, so the fact lives there rather than in a new
    convention. It is machine-independent by construction,
    which is exactly what the git remote is not.
    """

    try:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            data = tomllib.load(handle)

    except (OSError, tomllib.TOMLDecodeError):
        return None

    url = (
        data.get("project", {})
        .get("urls", {})
        .get("Repository")
    )

    if not url:
        return None

    url = str(url).strip()

    if not is_publishable_url(url):
        print(
            f"repository_url: pyproject declares {url!r}, which "
            "is not a public location — ignoring it.",
            file=sys.stderr,
        )
        return None

    return url


def repository_url() -> str:
    """
    Canonical public location of the project.

    This is a discovery field: where a reader goes to find
    AIStack. It is not the governance SPOT, which may be
    private and unreachable. Verification of a projection
    rests on source_commit and content_hash, never on a URL.

    AISTACK_REPOSITORY_URL carries the public canonical URL.
    The git remote is only a fallback, and a fallback that
    resolves to a private or loopback address is **refused**
    rather than published.

    That refusal is the point. Until 2026-08-21 this function
    documented the risk — "may expose an internal address,
    which must never be published inside a bundle" — and did
    nothing about it. A bundle generated on the SPOT host
    therefore carried `ssh://git@127.0.0.1:2222/...`, which is
    both useless to a consumer and a description of internal
    topology. The rule existed; only the discipline of whoever
    ran the command enforced it.

    An undeclared URL is a governed state (FDN-0003 Article 12).
    A wrong one is not.
    """

    override = os.getenv(
        "AISTACK_REPOSITORY_URL",
    )

    if override:
        return override.strip()

    declared = declared_repository_url()

    if declared:
        return declared

    try:
        remote = subprocess.check_output(
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

    if not is_publishable_url(remote):
        print(
            f"repository_url: refusing to publish {remote!r} — "
            "it is a private or loopback address. Set "
            "AISTACK_REPOSITORY_URL to the public canonical URL.",
            file=sys.stderr,
        )
        return "unknown"

    return remote


def main() -> None:

    sys.path.insert(
        0,
        str(ROOT / "src"),
    )


    from aistack.conformance.inventory import take_inventory

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


    # The projection carries the contract architecture measured
    # at generation. FDN-0011 requires technical debt to be
    # derived; carrying the derivation here is what makes it
    # published rather than available to whoever thinks to run a
    # command, and an agent handed only this bundle can state the
    # debt of the heritage it received.
    service = DefaultContextBundleService(
        transfer_service=transfer_service,
        measure_contracts=take_inventory,
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
