from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from aistack.kernel.catalog import Catalog
from aistack.selection.subtree import SubtreeResolution


# What belongs to the synchronisation tool rather than to the
# selection, at any depth of the target.
#
# `.stfolder` is how Syncthing recognises a folder it manages;
# removing it makes the folder stop syncing. The previous
# generator preserved it by name and nothing else, which was
# enough because it never descended.
SYNC_ARTEFACTS = frozenset({".stfolder", ".stignore", ".stversions"})


@dataclass(frozen=True)
class MaterialisationReport:
    """
    What the materialisation did, or refused to do.

    Returned rather than printed. The previous generator printed
    `COPY`, `LINK` and `SKIP` lines to standard output, which on
    the reference host means the log of a web application nobody
    reads — and the screen that ordered the work had nothing to
    show for it. The UI runs on a host that cannot be observed
    from where this code is reviewed; what it displays is the only
    instrument shared by both sides.

    `refused` is a sentence and not a flag. When it is non-empty
    nothing was written, and the sentence says why in terms the
    owner can act on.
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
    target_root: Path,
    media_extensions: frozenset[str],
    preserve_names: frozenset[str] = SYNC_ARTEFACTS,
    dry_run: bool = False,
) -> MaterialisationReport:
    """
    Bring the target folder to exactly what the selection designates.

    **Incremental, and that is not an optimisation.** The
    generator this replaces held `clean=True`: it emptied the
    target and copied the whole selection back, every time. On the
    owner's library that is 118 Gio erased and rewritten at each
    click — and Syncthing, doing its job, would propagate the
    deletion to the phone and then the re-appearance, over a VPN.
    The target folder was last written on 2026-07-13 and holds the
    first nine identifiers of the selection file: a run that
    emptied the folder, started rewriting it in file order, and
    stopped at the ninth. Repairing that button without changing
    its shape would have replayed it at scale.

    So: create what is missing, remove what is no longer
    designated, leave everything else untouched. A selection that
    did not change costs no write, and Syncthing sees nothing.

    **Hard links, decided 2026-08-29 by the owner.** Source and
    target sit on the same filesystem — `/dev/sdb1` on the
    reference host — so a link costs no bytes and no copy time.
    Syncthing reads a linked file as any other file: the phone
    receives real bytes and keeps them when the server is off.

    That decision has one failure mode, and this closes it. A tag
    editor that *replaces* a file rather than editing it in place
    leaves the target pointing at the old content, silently. Every
    file already present is therefore checked by inode, and
    relinked when it no longer shares one with its source. Two
    stats per file, against a library where a full traversal takes
    1,4 s.

    **The filesystem is verified before anything is written.**
    Hard links cannot cross filesystems, and the error a failed
    link raises names a file rather than the reason. The check
    names the reason, refuses, and writes nothing — the day the
    owner moves either directory to another disk, that is what he
    will read.
    """

    root = Path(catalog.metadata.get("root", ""))

    refusal = _refuse(root, target_root, dry_run)

    if refusal:
        return MaterialisationReport(refused=refusal, dry_run=dry_run)

    desired = _desired(catalog, resolution, media_extensions)

    present = _present(target_root, preserve_names)

    return _reconcile(desired, present, target_root, dry_run)


def _refuse(root: Path, target_root: Path, dry_run: bool) -> str:
    """
    Everything checked before a single byte is written.

    The filesystem comparison is made against the nearest existing
    ancestor of the target, so a dry run answers it too — and so
    the answer arrives before a directory is created on a disk
    that could never have held the links anyway.
    """

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

    Read from the filesystem rather than from the observation: the
    catalog carries counts, not names, and carrying 25 586 file
    names through it to save one directory listing per selected
    node would be a projection nobody asked for.

    The nodes are `covered`, so each file appears once — a node
    contributes only what lies directly inside it, and covered
    nodes do not overlap.
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

            if entry.suffix.lower() not in extensions:
                continue

            desired[f"{node}/{entry.name}"] = entry

    return desired


def _present(target_root: Path, preserve_names: frozenset[str]) -> set[str]:
    """
    Every file already in the target, minus what belongs to the
    synchronisation tool.

    Preserved by name at any depth, not only at the top. The
    previous generator preserved `.stfolder` at the root because
    it never went deeper; this one walks the whole target, and a
    rule that held by accident is a rule that breaks when the
    accident stops.
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
    Directories left empty by a removal.

    A folder emptied of its tracks but still present is a node the
    phone keeps showing and the screen no longer knows about.
    Removed bottom-up, and only when empty — nothing here decides
    that a directory is unwanted, it only notices that nothing is
    left in it.

    Not attempted in a dry run, and the report says so by leaving
    the list empty: nothing was removed, so nothing is empty that
    was not already, and reporting the directories that happen to
    be empty today as *would be pruned* would be a claim about a
    state that does not exist.

    Never the target root itself.
    """

    if dry_run:
        return []

    pruned: list[str] = []

    for current, subdirectories, filenames in os.walk(
        target_root, topdown=False
    ):

        if Path(current) == target_root:
            continue

        if filenames or subdirectories:
            continue

        relative = os.path.relpath(current, target_root)

        pruned.append(relative)

        try:
            os.rmdir(current)

        except OSError:
            pruned.pop()

    return pruned
