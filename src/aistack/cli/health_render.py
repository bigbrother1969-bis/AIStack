from __future__ import annotations

import socket
from pathlib import Path

from aistack.generators.health import HealthHtmlArtifactGenerator
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.providers.filesystem import StorageProvider, storage_thresholds_for_host
from aistack.runtime.evaluate_storage import evaluate_storage
from aistack.runtime.storage_shortage import find_storage_shortage

# `OPS-0005`'s own declared thresholds — the same file
# `aistack.cli.runtime_diagnose.DEFAULT_STORAGE_THRESHOLDS` reads.
# Declared again here rather than imported from that module: no CLI
# in this package imports another (`architecture_render.py` composes
# `DockerRuntimeCatalogBuilder`/`ComposeRuntimeCatalogBuilder` itself
# rather than importing `docker_catalog.main`), so each command keeps
# its own copy of the one path both happen to need, the same
# `Path(__file__).resolve()`-relative convention every other
# `DEFAULT_*` constant in this package already uses.
DEFAULT_STORAGE_THRESHOLDS = (
    Path(__file__).resolve().parents[1]
    / "providers"
    / "filesystem"
    / "definitions"
    / "storage_thresholds.yml"
)

# `PLAN-J7` § 1 (`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`): the
# closed domain vocabulary the owner named before any code —
# "stockage, services, backup/PRA, GPU" — not this module's own
# invention. Storage is the only one instrumented so far (`PLAN-J7`
# § 6); the other three carry this exact note, never a false
# "healthy" (`FDN-0003` Article 12).
NOT_YET_INSTRUMENTED = (
    "aucun cas réel n'a encore été cité par le propriétaire pour ce "
    "domaine (GOV-P-001) ; aucun code ne l'observe pour l'instant"
)


def storage_domain(hostname: str) -> HealthDomain:
    """
    `PLAN-J7` § 6's own domain, built from the same primitives
    `aistack.cli.runtime_diagnose` already wires into its own report:
    `storage_thresholds_for_host` narrows the fleet-wide file to this
    host, `StorageProvider` reads it, `find_storage_shortage` decides
    which mounts crossed `OPS-0005`, `evaluate_storage` states the
    finding. A host with nothing declared, or a missing/unreadable
    definition, is `instrumented=False` with the same note
    `storage_thresholds_for_host` already names — the same absence,
    stated the same way, whichever command asks.
    """

    thresholds, note = storage_thresholds_for_host(
        DEFAULT_STORAGE_THRESHOLDS, hostname
    )

    if not thresholds:
        return HealthDomain(name="Stockage", instrumented=False, note=note)

    usage = StorageProvider().collect_usage(
        tuple(threshold.mount for threshold in thresholds)
    )
    shortages = find_storage_shortage(usage, thresholds)

    return HealthDomain(
        name="Stockage", instrumented=True, findings=evaluate_storage(shortages)
    )


def build_cockpit(hostname: str) -> HealthCockpit:
    return HealthCockpit(
        domains=(
            storage_domain(hostname),
            HealthDomain(
                name="Services", instrumented=False, note=NOT_YET_INSTRUMENTED
            ),
            HealthDomain(
                name="Sauvegarde / PRA",
                instrumented=False,
                note=NOT_YET_INSTRUMENTED,
            ),
            HealthDomain(name="GPU", instrumented=False, note=NOT_YET_INSTRUMENTED),
        )
    )


def main() -> None:
    """
    `PLAN-J7` § 6.4/6.5: the cockpit visuel, decided with the owner
    2026-09-11 to render real findings rather than a score — the
    scoring model `PLAN-J7` § 1 still leaves undeclared, and a single
    instrumented domain has nothing to weigh a score against yet.
    """

    cockpit = build_cockpit(socket.gethostname())

    output_path = HealthHtmlArtifactGenerator().generate(
        cockpit=cockpit,
        output_path=Path("reports/generated/health.html"),
    )

    print(f"Health cockpit written to {output_path}")


if __name__ == "__main__":
    main()
