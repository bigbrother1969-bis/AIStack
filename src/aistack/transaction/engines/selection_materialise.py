"""
Knowledge Transaction - the engine of `selection.materialise`.

Brings a device's folder to exactly what a selection designates, with
hard links: creates what is missing, relinks what no longer shares its
source's inode, removes what is no longer designated, prunes the
directories left empty. What it would do is decided by
`aistack.generators.filesystem.hardlink.plan_materialisation`, which writes
nothing; this is the one place that acts. It refuses, writing nothing, when
the plan refuses; a file it cannot link or remove goes in the report's
`failed`, not in an exception. One run at a time per target.
"""

from __future__ import annotations

import os
from pathlib import Path

from aistack.generators.filesystem.hardlink import (
    MaterialisationReport,
    plan_materialisation,
    target_lock,
)
from aistack.transaction.contracts.selection_materialise import SelectionMaterialise
from aistack.transaction.interfaces.operation_engine import OperationEngine


class SelectionMaterialiseEngine(OperationEngine):
    """Returns the `MaterialisationReport`."""

    def execute(self, payload: object) -> object:
        if not isinstance(payload, SelectionMaterialise):
            raise TypeError("SelectionMaterialiseEngine expects a SelectionMaterialise payload.")

        target_root = payload.target_root

        with target_lock(target_root):

            plan = plan_materialisation(
                payload.catalog,
                payload.resolution,
                payload.capacity,
                target_root,
                payload.media_extensions,
                payload.preserve_names,
            )

            if plan.refused:
                return MaterialisationReport(refused=plan.refused)

            if not target_root.exists():

                try:
                    target_root.mkdir(parents=True)

                except OSError as error:
                    return MaterialisationReport(
                        refused=f"the target folder cannot be created: {error}"
                    )

            failed: list[tuple[str, str]] = []

            for relative in (*plan.linked, *plan.relinked):

                why = _link(plan.desired[relative], target_root / relative)

                if why:
                    failed.append((relative, why))

            for relative in plan.removed:

                why = _unlink(target_root / relative)

                if why:
                    failed.append((relative, why))

            pruned = _prune(target_root)

        return MaterialisationReport(
            linked=plan.linked,
            relinked=plan.relinked,
            removed=plan.removed,
            pruned=tuple(pruned),
            unchanged=plan.unchanged,
            failed=tuple(failed),
        )


def _link(source: Path, target: Path) -> str:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists() or target.is_symlink():
            target.unlink()

        os.link(source, target)

    except OSError as error:
        return str(error)

    return ""


def _unlink(target: Path) -> str:
    try:
        target.unlink()

    except OSError as error:
        return str(error)

    return ""


def _prune(target_root: Path) -> list[str]:
    """
    Remove directories left empty, bottom-up, never the target root.

    Emptiness is read from disk at each visit, not from `os.walk`'s tuple:
    with `topdown=False` that tuple still lists subdirectories already
    removed earlier in the pass.
    """

    pruned: list[str] = []

    for current, _subdirectories, _filenames in os.walk(target_root, topdown=False):

        if Path(current) == target_root:
            continue

        try:
            if os.listdir(current):
                continue

        except OSError:
            continue

        relative = os.path.relpath(current, target_root)

        pruned.append(relative)

        try:
            os.rmdir(current)

        except OSError:
            pruned.pop()

    return pruned
