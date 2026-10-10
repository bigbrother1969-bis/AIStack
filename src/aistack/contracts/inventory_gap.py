from __future__ import annotations

from dataclasses import dataclass

# The two directions of a mismatch.
DISCOVERED_UNDECLARED = "discovered_undeclared"
DECLARED_UNDISCOVERED = "declared_undiscovered"
KINDS = (DISCOVERED_UNDECLARED, DECLARED_UNDISCOVERED)


@dataclass(frozen=True)
class InventoryGap:
    """
    One mismatch between the declared inventory
    (`service_categorization.yml`) and the containers found running.

    `DISCOVERED_UNDECLARED`: a running container (local, or on a LAN host
    from the last `network_docker_discover`) that no service declares.
    `DECLARED_UNDISCOVERED`: a declared service whose container was not
    found running.

    `container` is always set. `service` is set only for
    `DECLARED_UNDISCOVERED`. `host` is set only for a remote discovered
    container; `None` means this machine or not applicable.

    Gaps are never written back to the declared file; the owner edits it.
    """

    kind: str
    container: str
    service: str | None = None
    host: str | None = None

    def __post_init__(self) -> None:
        if not self.kind:
            raise ValueError("InventoryGap requires a kind")

        if self.kind not in KINDS:
            raise ValueError(
                f"InventoryGap.kind must be one of {KINDS}, not "
                f"{self.kind!r}"
            )

        if not self.container.strip():
            raise ValueError(
                "InventoryGap requires a non-blank container — it is "
                "the identity the gap is about"
            )

        if self.kind == DECLARED_UNDISCOVERED and not (self.service or "").strip():
            raise ValueError(
                "a declared_undiscovered gap names the declared service "
                "it came from; this one names none"
            )

        if self.kind == DISCOVERED_UNDECLARED and self.service is not None:
            raise ValueError(
                "a discovered_undeclared gap names no declared service — "
                "that absence is exactly what makes it a gap"
            )
