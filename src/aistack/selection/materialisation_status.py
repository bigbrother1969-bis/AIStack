from __future__ import annotations

from aistack.generators.filesystem.hardlink import MaterialisationReport
from aistack.selection.subtree import SubtreeResolution


def materialized_nodes(
    report: MaterialisationReport, resolution: SubtreeResolution
) -> frozenset[str]:
    """
    Which covered nodes already hold everything the selection
    designates for them.

    Read from a dry-run `MaterialisationReport` rather than
    walking the target a second time: `materialise_by_hardlink`
    already compared what is desired against what is present, and
    `report.linked` already says, file by file, what a covered
    node is still missing. A node with none of its own files in
    `linked` has nothing outstanding — `relinked` files still
    count as present, since a stale inode is a file the phone can
    already see, only not the current one.

    A node that contributes no files of its own — an organising
    directory whose media all lives under its children, `Classique`
    over `Classique/Bach` — is vacuously counted as holding
    everything: there is nothing declared for it to be missing.

    **Not a claim about the phone.** This is what the target
    folder on the server holds. Whether the daemon has propagated
    it is the separate, folder-wide fact `SyncthingProvider`
    reports — decided 2026-09-03, after the API proved it can only
    answer for the whole folder, never file by file, so the two
    do not collapse into one line on the screen.
    """

    missing = {relative.rsplit("/", 1)[0] for relative in report.linked}

    return frozenset(
        node for node in resolution.covered if node not in missing
    )
