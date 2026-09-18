"""
`verify_uploads` — P2 of `claude/PLAN-PHOTOS-IPHONE-NEXTCLOUD-IMMICH-
2026-09-18.md`: confirm that a file `NextcloudProvider.collect()`
reported is really, fully present on Nextcloud, before anything
downstream (P5, then P6's Shortcuts-driven deletion) treats it as
safe to erase from the phone.

**Why this exists as its own step, separate from `collect()`.**
`ARC-P-012` keeps a provider's `collect()` to observation only — it
already refuses to interpret PROPFIND's answer into "safe" or
"unsafe" (`provider.py`'s own docstring). Qualifying an observation
into a decision is a second, separate step in this codebase (the same
split `aistack.runtime.evaluate` draws between collecting evidence
and correlating it into a `RuntimeFinding`) — this module is that
step for the photo pipeline, kept out of `aistack.runtime` because
`RuntimeFinding.qualifications` is a closed vocabulary owned by
`OPS-0004` (technical debt, energy inefficiency, sustainability
anomaly, deployment misconfiguration); "a photo is safe to delete"
is not one of those four, and forcing it into that vocabulary would
be exactly the invention `GOV-P-001` forbids.

**What "verified" means here, honestly.** The one thing PROPFIND
cannot be trusted alone for is size: `PLAN-…IMMICH-2026-09-18.md`'s
own § *Pourquoi pas l'app iOS Nextcloud* names the general failure
mode — a single unconfirmed indicator (the app's own "uploaded"
status) silently wrong. So this recoups `PROPFIND`'s reported
`getcontentlength` against a second, independent request —
`NextcloudProvider.download`'s actual byte count from a real `GET` —
and a file is `verified` only when the two agree. There is nothing on
AIStack's side to compare the `sha256` this computes *against* (the
phone's own copy never reaches this provider), so it travels in the
result for the audit trail, not as part of today's pass/fail — a
future jalon that gains an independent second source for a file's
content could tighten this without changing this module's shape.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Downloader = Callable[[str], dict[str, Any]]


def verify_uploads(
    files: list[dict[str, Any]],
    download: Downloader,
) -> list[dict[str, Any]]:
    """
    `files` is `NextcloudProvider.collect()["nextcloud"]["files"]`;
    `download` is ordinarily `NextcloudProvider.download`, passed in
    rather than called directly so this stays a pure decision over
    two already-collected facts, testable without a socket.

    Every file in, one verification entry out — a file that fails is
    reported with why, never dropped, the same "keep the half that
    arrived" discipline `SyncthingProvider` established.
    """

    verified: list[dict[str, Any]] = []

    for file in files:
        outcome = download(file["name"])

        if not outcome["downloaded"]:
            verified.append(
                {
                    "name": file["name"],
                    "verified": False,
                    "reason": outcome["reason"],
                    "size": file.get("size"),
                    "sha256": None,
                }
            )
            continue

        reported_size = file.get("size")
        downloaded_size = outcome["downloaded_size"]

        if reported_size is None:
            verified.append(
                {
                    "name": file["name"],
                    "verified": False,
                    "reason": (
                        "Nextcloud did not report a size for this file "
                        "to compare the download against"
                    ),
                    "size": downloaded_size,
                    "sha256": outcome["sha256"],
                }
            )
            continue

        if downloaded_size != reported_size:
            verified.append(
                {
                    "name": file["name"],
                    "verified": False,
                    "reason": (
                        f"PROPFIND reported {reported_size} bytes but "
                        f"the download was {downloaded_size} bytes"
                    ),
                    "size": downloaded_size,
                    "sha256": outcome["sha256"],
                }
            )
            continue

        verified.append(
            {
                "name": file["name"],
                "verified": True,
                "reason": "",
                "size": downloaded_size,
                "sha256": outcome["sha256"],
            }
        )

    return verified
