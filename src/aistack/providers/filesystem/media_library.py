from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Default media extensions for a caller that declares none; the
# application definition normally supplies its own.
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

# An extension set containing this counts every file as media (the
# generalized sync's `any` contents, `ADR-0022`).
EVERY_FILE = "*"


@dataclass
class _Counted:
    """What one directory yielded, recognised and not."""

    media_files: int = 0
    media_bytes: int = 0
    failures: int = 0
    other_files: int = 0
    unrecognized: dict[str, int] = field(default_factory=dict)


class MediaLibraryProvider:
    """Observe a media library on a filesystem and report every directory.

    Every directory is reported, media or not; `MediaLibraryCatalogBuilder`
    decides which are selectable. Each directory carries `media_files`
    (direct) and `total_media_files` (with descendants), gathered in one
    walk with no cache, so the catalog is always current (about 1.4 s for
    30,000 files).

    Symlinks inside the tree are not followed (double counting, loops).
    What is not observed is counted, not dropped: `unreadable`,
    `symlinks_not_followed`, `other_files` and `unrecognized_extensions`,
    so a format missing from the extension list shows up in the
    observation instead of silently emptying a directory.
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
        """Every directory with direct and cumulative media counts.

        Bottom-up so children's totals are known before their parent's.
        Sorted by path, since `os.walk` order depends on the filesystem.
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
                    # Not followed: double counting, possible loop.
                    symlinks += 1
                    continue

                child = self._join(relative, name)

                if child not in totals:
                    # Announced but never visited: unreadable or removed
                    # mid-walk. Counted, not assumed empty.
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
                # Distinguishes unrecognised files from an empty directory.
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
        """Count the media files in one directory, and the files left out
        by extension."""

        counted = _Counted()

        for name in filenames:

            extension = Path(name).suffix.lower()

            if extension not in self.media_extensions and EVERY_FILE not in self.media_extensions:
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
