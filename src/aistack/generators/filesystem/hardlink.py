"""
What a materialisation would do, read from the disk, writing nothing.

Doing it is the Kernel's operation `selection.materialise`
(`aistack.transaction.engines.selection_materialise`): this module decides,
that one acts (`GOV-P-002`, `ADR-0027` § 11).
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from aistack.kernel.catalog import Catalog
from aistack.selection.capacity import CapacityVerdict
from aistack.selection.subtree import SubtreeResolution


# Syncthing's own files, preserved at any depth of the target.
# Removing `.stfolder` makes the folder stop syncing.
SYNC_ARTEFACTS = frozenset({".stfolder", ".stignore", ".stversions"})


_TARGET_LOCKS_GUARD = threading.Lock()
_TARGET_LOCKS: dict[str, threading.Lock] = {}


@contextmanager
def target_lock(target_root: Path) -> Iterator[None]:
    """Hold the target's lock: see `_lock_for`."""

    with _lock_for(target_root):
        yield


def _lock_for(target_root: Path) -> threading.Lock:
    """
    One lock per target, so two materialisations never write to the
    same folder at once.

    Starlette runs the synchronous `/save` route in a thread pool, so
    two quick clicks run concurrently, and `_link`/`_unlink` are
    check-then-act. Keyed by target so a dry run for one target does
    not wait on a write to another.
    """

    key = str(target_root)

    with _TARGET_LOCKS_GUARD:

        if key not in _TARGET_LOCKS:
            _TARGET_LOCKS[key] = threading.Lock()

        return _TARGET_LOCKS[key]


@dataclass(frozen=True)
class MaterialisationReport:
    """
    What the materialisation did, or refused to do, for the screen to
    display.

    `refused` is a sentence, not a flag: when non-empty, nothing was
    written and it says why in terms the owner can act on.
    """

    linked: tuple[str, ...] = ()
    relinked: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    pruned: tuple[str, ...] = ()
    unchanged: int = 0
    failed: tuple[tuple[str, str], ...] = ()
    refused: str = ""
    dry_run: bool = False


@dataclass(frozen=True)
class MaterialisationPlan:
    """
    What bringing the target to the selection takes: the files to link
    (`linked`: absent; `relinked`: present but no longer the source's
    inode), those to remove, and how many are right already. `desired`
    gives each target path its source. When `refused` is non-empty, it
    says why and nothing else is filled.
    """

    refused: str = ""
    desired: dict[str, Path] = field(default_factory=dict)
    linked: tuple[str, ...] = ()
    relinked: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    unchanged: int = 0


def plan_materialisation(
    catalog: Catalog,
    resolution: SubtreeResolution,
    capacity: CapacityVerdict,
    target_root: Path,
    media_extensions: frozenset[str],
    preserve_names: frozenset[str] = SYNC_ARTEFACTS,
) -> MaterialisationPlan:
    """
    Read what bringing the target folder to exactly what the selection
    designates, with hard links, takes. Writes nothing.

    Incremental: create what is missing, remove what is no longer
    designated, leave the rest untouched, so an unchanged selection
    causes no write for Syncthing to propagate. A file present in the
    target is to be relinked when it no longer shares its source's inode
    (a tag editor may replace a file instead of editing it in place).

    Refuses when the selection exceeds `capacity`, or when source and
    target are on different filesystems (hard links cannot cross them,
    and the raw error would not say so).
    """

    root = Path(catalog.metadata.get("root", ""))

    refusal = _refuse(root, target_root, capacity)

    if refusal:
        return MaterialisationPlan(refused=refusal)

    desired = _desired(catalog, resolution, media_extensions)

    present = _present(target_root, preserve_names)

    linked: list[str] = []
    relinked: list[str] = []
    unchanged = 0

    for relative in sorted(desired):

        if relative not in present:
            linked.append(relative)

        elif _same_file(desired[relative], target_root / relative):
            unchanged += 1

        else:
            relinked.append(relative)

    return MaterialisationPlan(
        desired=desired,
        linked=tuple(linked),
        relinked=tuple(relinked),
        removed=tuple(sorted(present - set(desired))),
        unchanged=unchanged,
    )


def preview_materialisation(
    catalog: Catalog,
    resolution: SubtreeResolution,
    capacity: CapacityVerdict,
    target_root: Path,
    media_extensions: frozenset[str],
    preserve_names: frozenset[str] = SYNC_ARTEFACTS,
) -> MaterialisationReport:
    """The plan as a report (`dry_run`): what the screens show before anything is done."""

    with _lock_for(target_root):

        plan = plan_materialisation(
            catalog, resolution, capacity, target_root, media_extensions, preserve_names
        )

    if plan.refused:
        return MaterialisationReport(refused=plan.refused, dry_run=True)

    return MaterialisationReport(
        linked=plan.linked,
        relinked=plan.relinked,
        removed=plan.removed,
        unchanged=plan.unchanged,
        dry_run=True,
    )


def _refuse(
    root: Path,
    target_root: Path,
    capacity: CapacityVerdict,
) -> str:
    """
    Return why materialisation must not run, or `""`.

    Capacity is checked first, as the refusal a human can act on. The
    filesystem is compared against the target's nearest existing
    ancestor, so the answer comes before any directory is created on a
    disk that could not hold the links.
    """

    if not capacity.fits:
        return (
            "the selection is larger than the declared capacity: "
            f"{capacity.selected_bytes} bytes selected against "
            f"{capacity.declared_bytes} declared, "
            f"{capacity.overflow_bytes} bytes too many"
        )

    if not root or not root.is_dir():
        return f"the library root does not exist or is not a directory: {root}"

    if target_root.exists() and not target_root.is_dir():
        return f"the target is not a directory: {target_root}"

    probe = target_root

    while not probe.exists() and probe != probe.parent:
        probe = probe.parent

    if not probe.exists():
        return f"nothing on the path to the target exists: {target_root}"

    if root.stat().st_dev != probe.stat().st_dev:
        return (
            "the library and the target are on different filesystems, "
            "and a hard link cannot cross one: "
            f"{root} and {target_root}"
        )

    return ""


def _desired(
    catalog: Catalog,
    resolution: SubtreeResolution,
    media_extensions: frozenset[str],
) -> dict[str, Path]:
    """
    Every media file the selection designates, by target path.

    Read from the filesystem, since the catalog carries counts, not
    names. Covered nodes do not overlap and each contributes only its
    direct files, so each file appears once.
    """

    sources = {item.id: item.source for item in catalog.items}

    extensions = frozenset(
        extension.lower() for extension in media_extensions
    )

    desired: dict[str, Path] = {}

    for node in resolution.covered:

        directory = Path(sources.get(node, ""))

        if not directory.is_dir():
            continue

        for entry in sorted(directory.iterdir()):

            if entry.is_dir() or entry.is_symlink():
                continue

            if entry.suffix.lower() not in extensions and "*" not in extensions:
                continue

            desired[f"{node}/{entry.name}"] = entry

    return desired


def _present(target_root: Path, preserve_names: frozenset[str]) -> set[str]:
    """
    Every file already in the target, minus `preserve_names` at any
    depth.
    """

    present: set[str] = set()

    for current, subdirectories, filenames in os.walk(target_root):

        subdirectories[:] = [
            name for name in subdirectories if name not in preserve_names
        ]

        relative = os.path.relpath(current, target_root)

        prefix = "" if relative == "." else f"{relative}/"

        for name in filenames:

            if name in preserve_names:
                continue

            present.add(f"{prefix}{name}")

    return present


def _same_file(source: Path, target: Path) -> bool:
    try:
        return source.stat().st_ino == target.stat().st_ino

    except OSError:
        return False
