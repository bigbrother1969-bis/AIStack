from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# The extensions this provider counts as media, and nothing else
# about them.
#
# A default, not a declaration: which extensions a given library
# holds is deployment knowledge and travels in the application
# definition, the same way its root does. This value is what an
# unconfigured caller gets, and every test that matters passes its
# own.
DEFAULT_MEDIA_EXTENSIONS = frozenset(
    {
        ".aac",
        ".aiff",
        ".ape",
        ".dts",
        ".flac",
        ".m4a",
        ".mp3",
        ".mpc",
        ".ogg",
        ".opus",
        ".wav",
        ".wma",
    }
)


@dataclass
class _Counted:
    """What one directory yielded, recognised and not."""

    media_files: int = 0
    media_bytes: int = 0
    failures: int = 0
    other_files: int = 0
    unrecognized: dict[str, int] = field(default_factory=dict)


class MediaLibraryProvider:
    """
    Observe a media library on a filesystem and report what is there.

    A provider observes. It does not qualify — `RepositoryProvider`
    says it in the same words, and FDN-0003 Article 4 is where both
    get it. So **every directory is reported**, including the ones
    that hold no media at all: `lost+found`, a game library, a
    folder of scanned covers. Deciding which of them is a
    selectable node is an interpretation, and it belongs to the
    Catalog builder that consumes this.

    The temptation to filter here is real and was measured. The
    owner's library, on 2026-08-29: 250 directories at the first
    level, 2644 in the whole tree, five levels deep, 30 015 files,
    and 1949 directories holding audio directly — 34 of them at
    the first level while only 17 have no subdirectory, so
    seventeen artists carry albums *and* loose tracks at once. No
    rule written from a shape guessed at the first level survives
    that tree, and a provider that had filtered would have hidden
    the evidence that says so.

    **Two counts per directory, and they answer different
    questions.** `media_files` is what lies directly inside;
    `total_media_files` includes every descendant. A screen that
    lets a human tick any node of the tree needs the second to
    show what ticking costs, and the first to tell a container
    apart from a leaf. Both are gathered in one walk, which on the
    reference host takes **1,05 s** for 2644 directories and
    30 015 files — measured 2026-08-29, on this provider.

    That figure replaces one this docstring carried for the length
    of a single commit. It said 87 ms, and 87 ms is what
    `find . -type f | wc -l` takes on the same tree: a directory
    traversal in C that stats no file. This walk stats every media
    file it counts. A figure measured on one command was written
    down to justify a decision about another — the failure this
    heritage names first, committed in the commit that cites it.

    Symbolic links are not followed. The library reached by one —
    `/media/Multimedia/Music` is a link to
    `/media/TechData/Storage/Music` on the reference host — is
    observed at the root it resolves to, but a link *inside* the
    tree would count its target twice and can close a loop.

    What is not observed is counted rather than dropped.
    `unreadable` says how many directories refused or vanished
    mid-walk, `symlinks_not_followed` how many were skipped by the
    rule above, `other_files` how many files a directory holds
    that this provider did not recognise, and
    `unrecognized_extensions` what those files were.

    **The last one exists because its absence cost a composer.**
    Until 2026-08-29 an unrecognised file left no trace, so an
    album holding twelve `.ape` tracks and an empty directory
    produced the same observation — zero — and the catalog rule
    excluded both while stating the same reason for each. The
    default list was plausible rather than measured, and a census
    run by hand on the owner's library found `.mpc`, `.ape` and
    `.dts` missing from it: 26 nodes and 6,84 Gio absent from the
    catalog, `Classique/Schubert` entire among them, on a screen
    whose whole subject is fitting inside 64 Go.

    A list of extensions will be wrong again — this one is a
    default, and the governed value travels in the application
    definition. What changes is that the next missing format
    announces itself in the observation instead of waiting for
    someone to notice an absence.
    """

    provider_id = "aistack.provider.filesystem.media-library"
    provider_name = "Media Library Provider"

    def __init__(
        self,
        root: Path | str,
        media_extensions: frozenset[str] = DEFAULT_MEDIA_EXTENSIONS,
    ) -> None:
        self.root = Path(root)
        self.media_extensions = frozenset(
            extension.lower() for extension in media_extensions
        )

    def collect(self) -> dict[str, Any]:
        directories, unreadable, symlinks, unrecognized = self._walk()

        return {
            "provider": {
                "id": self.provider_id,
                "name": self.provider_name,
            },
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "library": {
                "root": str(self.root),
                "exists": self.root.is_dir(),
                "media_extensions": sorted(self.media_extensions),
                "unreadable": unreadable,
                "symlinks_not_followed": symlinks,
                "unrecognized_extensions": unrecognized,
                "directories": directories,
            },
        }

    def _walk(self) -> tuple[list[dict[str, Any]], int, int, dict[str, int]]:
        """
        Every directory of the tree, with its media counted twice.

        Bottom-up, because a directory's cumulative total is its
        own plus its children's and the children must be known
        first. `os.walk` visits each directory once either way;
        the order is what makes one pass enough.

        Sorted by path before returning. STD-0300 § 6 requires an
        unchanged input to produce an identical output, and
        `os.walk` yields whatever order the filesystem hands it —
        which differs between two hosts holding the same files.
        """

        if not self.root.is_dir():
            return [], 0, 0, {}

        totals: dict[str, tuple[int, int]] = {}
        entries: dict[str, dict[str, Any]] = {}
        unreadable = 0
        symlinks = 0
        unrecognized: dict[str, int] = {}

        walker = os.walk(self.root, topdown=False, onerror=lambda _: None)

        for current, subdirectories, filenames in walker:

            relative = self._relative(current)

            counted = self._count(current, filenames)

            unreadable += counted.failures

            for extension, count in counted.unrecognized.items():
                unrecognized[extension] = (
                    unrecognized.get(extension, 0) + count
                )

            total_files = counted.media_files
            total_bytes = counted.media_bytes

            for name in subdirectories:

                if os.path.islink(os.path.join(current, name)):
                    # Announced by `os.walk` and never visited,
                    # deliberately. Counting it would add its
                    # target's weight a second time, and a link
                    # upwards would not terminate.
                    symlinks += 1
                    continue

                child = self._join(relative, name)

                if child not in totals:
                    # A directory `os.walk` announced and never
                    # visited: unreadable, or removed between the
                    # two moments. Counted, not assumed empty.
                    unreadable += 1
                    continue

                child_files, child_bytes = totals[child]

                total_files += child_files
                total_bytes += child_bytes

            totals[relative] = (total_files, total_bytes)

            entries[relative] = {
                "relative_path": relative,
                "parent": self._parent(relative),
                "depth": 0 if relative == "" else len(Path(relative).parts),
                "media_files": counted.media_files,
                "media_bytes": counted.media_bytes,
                # A directory holding files this provider does not
                # recognise is a different fact from an empty one,
                # and the difference is what makes a missing
                # format announce itself.
                "other_files": counted.other_files,
                "total_media_files": total_files,
                "total_media_bytes": total_bytes,
            }

        return (
            [entries[key] for key in sorted(entries)],
            unreadable,
            symlinks,
            {key: unrecognized[key] for key in sorted(unrecognized)},
        )

    def _count(self, directory: str, filenames: list[str]) -> _Counted:
        """
        What is media here, and what was left out.

        The second half is the point. Until 2026-08-29 this
        returned only what it recognised, so a directory holding
        twelve `.ape` tracks and a directory holding nothing
        produced the same observation — zero — and the catalog
        rule above excluded both for the same stated reason. The
        owner had to run a census by hand to find that three audio
        formats were missing from the default list, one of which
        hid an entire composer.
        """

        counted = _Counted()

        for name in filenames:

            extension = Path(name).suffix.lower()

            if extension not in self.media_extensions:
                counted.other_files += 1
                counted.unrecognized[extension] = (
                    counted.unrecognized.get(extension, 0) + 1
                )
                continue

            try:
                counted.media_bytes += os.path.getsize(
                    os.path.join(directory, name)
                )

            except OSError:
                counted.failures += 1
                continue

            counted.media_files += 1

        return counted

    def _relative(self, path: str) -> str:
        relative = os.path.relpath(path, self.root)

        return "" if relative == "." else relative

    def _join(self, relative: str, name: str) -> str:
        return name if relative == "" else f"{relative}{os.sep}{name}"

    def _parent(self, relative: str) -> str:
        if relative == "":
            return ""

        return str(Path(relative).parent) if os.sep in relative else ""
