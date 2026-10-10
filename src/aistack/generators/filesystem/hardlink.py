from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from aistack.kernel.catalog import Catalog
from aistack.selection.capacity import CapacityVerdict
from aistack.selection.subtree import SubtreeResolution


# Syncthing's own files, preserved at any depth of the target.
# Removing `.stfolder` makes the folder stop syncing.
SYNC_ARTEFACTS = frozenset({".stfolder", ".stignore", ".stversions"})


_TARGET_LOCKS_GUARD = threading.Lock()
_TARGET_LOCKS: dict[str, threading.Lock] = {}


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


def materialise_by_hardlink(
    catalog: Catalog,
    resolution: SubtreeResolution,
    capacity: CapacityVerdict,
    target_root: Path,
    media_extensions: frozenset[str],
    preserve_names: frozenset[str] = SYNC_ARTEFACTS,
    dry_run: bool = False,
) -> MaterialisationReport:
    """
    Bring the target folder to exactly what the selection designates,
    using hard links.

    Incremental: create what is missing, remove what is no longer
    designated, leave the rest untouched, so an unchanged selection
    causes no write for Syncthing to propagate. A file present in the
    target is relinked when it no longer shares its source's inode (a
    tag editor may replace a file instead of editing it in place).

    Refuses, writing nothing, when the selection exceeds `capacity`,
    or when source and target are on different filesystems (hard links
    cannot cross them, and the raw error would not say so). Runs under
    a per-target lock (`_lock_for`).
    """

    with _lock_for(target_root):

        root = Path(catalog.metadata.get("root", ""))

        refusal = _refuse(root, target_root, capacity, dry_run)

        if refusal:
            return MaterialisationReport(refused=refusal, dry_run=dry_run)

        desired = _desired(catalog, resolution, media_extensions)

        present = _present(target_root, preserve_names)

        return _reconcile(desired, present, target_root, dry_run)


def _refuse(
    root: Path,
    target_root: Path,
    capacity: CapacityVerdict,
    dry_run: bool,
) -> str:
    """
    Return why materialisation must not run, or `""`.

    Capacity is checked first, as the refusal a human can act on. The
    filesystem is compared against the target's nearest existing
    ancestor, so a dry run checks it too and no directory is created
    on a disk that could not hold the links.
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

    if not target_root.exists() and not dry_run:

        try:
            target_root.mkdir(parents=True)

        except OSError as error:
            return f"the target folder cannot be created: {error}"

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


def _reconcile(
    desired: dict[str, Path],
    present: set[str],
    target_root: Path,
    dry_run: bool,
) -> MaterialisationReport:
    linked: list[str] = []
    relinked: list[str] = []
    removed: list[str] = []
    failed: list[tuple[str, str]] = []
    unchanged = 0

    for relative in sorted(desired):

        source = desired[relative]
        target = target_root / relative

        if relative in present:

            if _same_file(source, target):
                unchanged += 1
                continue

            relinked.append(relative)

        else:
            linked.append(relative)

        if dry_run:
            continue

        error = _link(source, target)

        if error:
            failed.append((relative, error))

    for relative in sorted(present - set(desired)):

        removed.append(relative)

        if dry_run:
            continue

        error = _unlink(target_root / relative)

        if error:
            failed.append((relative, error))

    pruned = _prune(target_root, dry_run)

    return MaterialisationReport(
        linked=tuple(linked),
        relinked=tuple(relinked),
        removed=tuple(removed),
        pruned=tuple(pruned),
        unchanged=unchanged,
        failed=tuple(failed),
        dry_run=dry_run,
    )


def _same_file(source: Path, target: Path) -> bool:
    try:
        return source.stat().st_ino == target.stat().st_ino

    except OSError:
        return False


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


def _prune(target_root: Path, dry_run: bool) -> list[str]:
    """
    Remove directories left empty, bottom-up, never the target root.

    Skipped in a dry run (empty list). Emptiness is read from disk at
    each visit, not from `os.walk`'s tuple: with `topdown=False` that
    tuple still lists subdirectories already removed earlier in the
    pass.
    """

    if dry_run:
        return []

    pruned: list[str] = []

    for current, _subdirectories, _filenames in os.walk(
        target_root, topdown=False
    ):

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
