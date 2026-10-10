from __future__ import annotations

from aistack.generators.filesystem.hardlink import MaterialisationReport
from aistack.selection.subtree import SubtreeResolution


def materialized_nodes(
    report: MaterialisationReport, resolution: SubtreeResolution
) -> frozenset[str]:
    """Covered nodes that already hold every file the selection designates
    for them.

    Read from a dry-run `MaterialisationReport`: a node with none of its own
    files in `report.linked` has nothing outstanding (`relinked` files count
    as present). A node with no files of its own (`Classique` over
    `Classique/Bach`) counts as complete.

    This describes the target folder on the server, not the phone; Syncthing
    propagation is a separate, folder-wide fact from `SyncthingProvider`.
    """

    missing = {relative.rsplit("/", 1)[0] for relative in report.linked}

    return frozenset(
        node for node in resolution.covered if node not in missing
    )
