from __future__ import annotations

from dataclasses import dataclass

# Two directions, both real (owner's own choice, "les deux sens",
# 1.6 tranche 3 cadrage, 2026-09-30) — never a third invented ahead of
# a real case (`ARC-P-006`).
DISCOVERED_UNDECLARED = "discovered_undeclared"
DECLARED_UNDISCOVERED = "declared_undiscovered"
KINDS = (DISCOVERED_UNDECLARED, DECLARED_UNDISCOVERED)


@dataclass(frozen=True)
class InventoryGap:
    """
    One mismatch between what AIStack's own inventory declares
    (`service_categorization.yml`) and what it actually finds running
    — 1.6 tranche 3 (R9, roadmap's own "Écarts d'inventaire → quai →
    validation → inventaire déclaré", 2026-09-30).

    **Two kinds, symmetric, both real (the owner's own choice at
    cadrage).** `DISCOVERED_UNDECLARED` — a container `find_inventory_
    gaps` found running, locally via `DockerProvider` or on another
    LAN host via the last `network_docker_discover` observation, that
    `service_categorization.yml` names in no service. `DECLARED_
    UNDISCOVERED` — the reverse: a declared service naming a container
    that neither source ever found running. Neither direction is
    treated as more authoritative than the other; each is exactly what
    it says, no more.

    **`container` is always set — it is the identity both sides are
    joined on.** `service` is set only for `DECLARED_UNDISCOVERED`
    (the declared service's own name — a `DISCOVERED_UNDECLARED`
    container has no declared service by definition, that is exactly
    what makes it a gap). `host` is set only when the discovering side
    knows one: a remote host `network_docker_discover` observed
    (`DISCOVERED_UNDECLARED` only) — `None` means "this machine"
    (local, via `DockerProvider`) for a `DISCOVERED_UNDECLARED` gap, or
    simply "not applicable" for a `DECLARED_UNDISCOVERED` one, since
    `service_categorization.yml` itself never names a host
    (`ServiceCategorizationDefinition`'s own docstring: "`server` alone
    still does not travel").

    **No validation, no auto-correction.** This register is never
    written back to `service_categorization.yml` by this codebase —
    the roadmap's own "validation" step is the owner reading these
    findings and editing the declared file by hand, the same
    discipline every prior tranche has held (`GOV-P-001`: the agent
    never pushes, and never edits a declared file on the owner's
    behalf either).
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
