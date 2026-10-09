"""
`sync.yml` (`ADR-0022`): the contents of this host, the destinations
they can be sent to, and where each pair's files are kept.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from aistack.config import configured
from aistack.providers.filesystem import DEFAULT_MEDIA_EXTENSIONS
from aistack.providers.filesystem.media_library import EVERY_FILE

SHIPPED = Path(__file__).resolve().parent / "definitions" / "sync.yml"
SYNC_DIR = ".aistack-sync"
GB = 1_000_000_000

SYNCTHING = "syncthing"
KINDLE = "kindle"
USB = "usb"
DESTINATION_KINDS = (SYNCTHING, KINDLE, USB)

# The files each kind of content holds; `any` takes every file.
KINDS: dict[str, frozenset[str]] = {
    "audio": DEFAULT_MEDIA_EXTENSIONS,
    "images": frozenset(
        {".jpg", ".jpeg", ".png", ".heic", ".heif", ".gif", ".webp", ".tif", ".tiff",
         ".bmp", ".dng", ".cr2", ".nef", ".arw", ".raf", ".orf", ".rw2"}
    ),
    "video": frozenset(
        {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".webm", ".wmv", ".mpg", ".mpeg",
         ".ts", ".srt", ".ass", ".sub", ".vtt"}
    ),
    "books": frozenset({".epub", ".pdf", ".mobi", ".azw", ".azw3", ".kfx", ".txt", ".djvu", ".fb2", ".rtf"}),
    "comics": frozenset({".cbz", ".cbr", ".cb7", ".cbt", ".pdf", ".epub", ".jpg", ".jpeg", ".png", ".webp"}),
    "documents": frozenset(
        {".pdf", ".doc", ".docx", ".odt", ".xls", ".xlsx", ".ods", ".ppt", ".pptx",
         ".odp", ".txt", ".md", ".rtf", ".csv", ".jpg", ".jpeg", ".png"}
    ),
}
ANY = "any"


@dataclass(frozen=True)
class Content:
    id: str
    title: dict[str, str]
    source: Path
    kind: str
    exclude: tuple[str, ...] = ()

    def label(self, lang: str) -> str:
        return self.title.get(lang) or next(iter(self.title.values()), self.id)


@dataclass(frozen=True)
class Destination:
    id: str
    title: dict[str, str]
    kind: str
    device: str = ""
    quota_bytes: int = 0

    def label(self, lang: str) -> str:
        return self.title.get(lang) or next(iter(self.title.values()), self.id)


@dataclass(frozen=True)
class SyncthingAccess:
    url: str
    api_key_env: str
    timeout_seconds: float = 5.0
    # host prefix → the prefix Syncthing sees, longest first.
    path_map: tuple[tuple[str, str], ...] = ()

    def seen_by_syncthing(self, host_path: Path) -> str:
        text = str(host_path)
        for host, inside in self.path_map:
            if text == host or text.startswith(host.rstrip("/") + "/"):
                return inside.rstrip("/") + text[len(host.rstrip("/")):]
        return text


@dataclass(frozen=True)
class PairOverride:
    target: Path | None = None
    folder: str = ""


@dataclass(frozen=True)
class SyncDeclaration:
    syncthing: SyncthingAccess | None
    contents: dict[str, Content]
    destinations: dict[str, Destination]
    pairs: dict[str, PairOverride] = field(default_factory=dict)

    def pair_ids(self) -> list[str]:
        """Every (content, destination), destinations first in declared order."""

        return [pair_id(c, d) for d in self.destinations for c in self.contents]


def pair_id(content: str, destination: str) -> str:
    return f"{content}--{destination}"


def split_pair(pair: str) -> tuple[str, str]:
    content, _, destination = pair.partition("--")
    return content, destination


def extensions(content: Content) -> frozenset[str]:
    """The extensions the content holds; `{EVERY_FILE}` for `any`."""

    return frozenset({EVERY_FILE}) if content.kind == ANY else KINDS[content.kind]


def mount_point(path: Path) -> Path:
    """The mount the path lives on: the highest ancestor on the same device."""

    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        device = probe.stat().st_dev
    except OSError:
        return probe
    while probe != probe.parent:
        try:
            if probe.parent.stat().st_dev != device:
                return probe
        except OSError:
            return probe
        probe = probe.parent
    return probe


def target_for(declaration: SyncDeclaration, content: str, destination: str) -> Path:
    override = declaration.pairs.get(pair_id(content, destination))
    if override is not None and override.target is not None:
        return override.target
    return mount_point(declaration.contents[content].source) / SYNC_DIR / destination / content


def folder_for(declaration: SyncDeclaration, content: str, destination: str) -> str:
    override = declaration.pairs.get(pair_id(content, destination))
    if override is not None and override.folder:
        return override.folder
    return f"aistack-{content}-{destination}"


def _title(raw: Any, fallback: str) -> dict[str, str]:
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {"fr": str(raw or fallback), "en": str(raw or fallback)}


def load_sync_declaration(path: Path | None = None) -> SyncDeclaration:
    source = path if path is not None else configured(SHIPPED)
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{source}: not a mapping")

    access = None
    raw = data.get("syncthing")
    if isinstance(raw, dict):
        if not raw.get("url"):
            raise ValueError(f"{source}: syncthing names no url")
        mapping = sorted(
            ((str(k), str(v)) for k, v in (raw.get("path_map") or {}).items()),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        access = SyncthingAccess(
            url=str(raw["url"]).rstrip("/"),
            api_key_env=str(raw.get("api_key_env") or ""),
            timeout_seconds=float(raw.get("timeout_seconds") or 5),
            path_map=tuple(mapping),
        )

    contents: dict[str, Content] = {}
    for name, raw in (data.get("contents") or {}).items():
        if not isinstance(raw, dict) or not raw.get("source"):
            raise ValueError(f"{source}: content `{name}` names no source")
        kind = str(raw.get("kind") or ANY)
        if kind != ANY and kind not in KINDS:
            raise ValueError(f"{source}: content `{name}`: unknown kind `{kind}` (known: {', '.join([*KINDS, ANY])})")
        if "--" in str(name):
            raise ValueError(f"{source}: content `{name}`: `--` is reserved")
        contents[str(name)] = Content(
            id=str(name),
            title=_title(raw.get("title"), str(name)),
            source=Path(str(raw["source"])),
            kind=kind,
            exclude=tuple(str(item) for item in raw.get("exclude") or ()),
        )

    destinations: dict[str, Destination] = {}
    for name, raw in (data.get("destinations") or {}).items():
        if not isinstance(raw, dict):
            raise ValueError(f"{source}: destination `{name}` is not a mapping")
        kind = str(raw.get("kind") or "")
        if kind not in DESTINATION_KINDS:
            raise ValueError(f"{source}: destination `{name}`: kind must be one of {', '.join(DESTINATION_KINDS)}")
        if kind == SYNCTHING and not raw.get("device"):
            raise ValueError(f"{source}: destination `{name}` names no Syncthing device")
        if "--" in str(name):
            raise ValueError(f"{source}: destination `{name}`: `--` is reserved")
        destinations[str(name)] = Destination(
            id=str(name),
            title=_title(raw.get("title"), str(name)),
            kind=kind,
            device=str(raw.get("device") or ""),
            quota_bytes=int(float(raw.get("quota_gb") or 0) * GB),
        )

    pairs: dict[str, PairOverride] = {}
    for name, raw in (data.get("pairs") or {}).items():
        content, _, destination = str(name).partition("/")
        if content not in contents or destination not in destinations:
            raise ValueError(f"{source}: pair `{name}` names no declared content/destination")
        raw = raw or {}
        pairs[pair_id(content, destination)] = PairOverride(
            target=Path(str(raw["target"])) if raw.get("target") else None,
            folder=str(raw.get("folder") or ""),
        )

    return SyncDeclaration(access, contents, destinations, pairs)


def excluded(content: Content, relative: str) -> bool:
    """Whether a directory of the content, relative to its source, is never offered."""

    parts = PurePosixPath(relative).parts
    return any(part in content.exclude for part in parts) or relative in content.exclude


def api_key(access: SyncthingAccess) -> str:
    return os.environ.get(access.api_key_env, "") if access.api_key_env else ""
