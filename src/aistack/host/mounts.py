"""
The disks and mounts the AIStack host sees, and which of them holds
each thing AIStack keeps (asked by the owner, 2026-10-04: from Settings,
see every disk and mount reachable from the server, to choose later
where each component goes — choosing is 1.8's).

Read from `/proc/self/mounts` and `os.statvfs`, never from a command:
pseudo filesystems and Docker's own layers are left out. A network
mount that does not answer within two seconds is shown as such, never
waited on.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

PSEUDO_TYPES = frozenset(
    {
        "proc", "sysfs", "devtmpfs", "devpts", "tmpfs", "securityfs", "cgroup", "cgroup2",
        "pstore", "bpf", "autofs", "mqueue", "hugetlbfs", "debugfs", "tracefs", "fusectl",
        "configfs", "binfmt_misc", "overlay", "nsfs", "squashfs", "efivarfs", "ramfs",
        "rpc_pipefs", "nfsd", "fuse.portal", "fuse.gvfsd-fuse", "fuse.lxcfs", "selinuxfs",
    }
)
# Docker's own layers and the snap images: what the host runs on, not
# where anyone would put anything.
HIDDEN_PREFIXES = ("/var/lib/docker/", "/run/docker/", "/snap/", "/var/snap/", "/run/user/")
# Inside a container: the files Docker binds for its own name service.
HIDDEN_POINTS = frozenset({"/etc/hosts", "/etc/hostname", "/etc/resolv.conf"})
NETWORK_TYPES = frozenset({"nfs", "nfs4", "cifs", "smb3", "fuse.sshfs", "9p"})
STATVFS_TIMEOUT = 2.0

_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="aistack-statvfs")


@dataclass(frozen=True)
class Mount:
    device: str
    point: str
    fstype: str
    read_only: bool

    @property
    def network(self) -> bool:
        return self.fstype in NETWORK_TYPES


@dataclass(frozen=True)
class Usage:
    total: int
    free: int


@dataclass(frozen=True)
class MountRow:
    mount: Mount
    usage: Usage | None  # None: did not answer in time
    components: tuple[str, ...]


def _unescape(field: str) -> str:
    # /proc/mounts writes a space as \040, a tab as \011, a newline as \012.
    return field.replace("\\040", " ").replace("\\011", "\t").replace("\\012", "\n").replace("\\134", "\\")


def parse_mounts(text: str) -> list[Mount]:
    """The real mounts of a `/proc/mounts` text, one per mount point (the
    last one mounted there wins), sorted by mount point."""

    found: dict[str, Mount] = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        device, point, fstype, options = _unescape(fields[0]), _unescape(fields[1]), fields[2], fields[3]
        if (
            fstype in PSEUDO_TYPES
            or point in HIDDEN_POINTS
            or any((point + "/").startswith(prefix) for prefix in HIDDEN_PREFIXES)
        ):
            continue
        found[point] = Mount(device, point, fstype, "ro" in options.split(","))
    return sorted(found.values(), key=lambda mount: mount.point)


def holder(path: Path, mounts: list[Mount]) -> Mount | None:
    """The mount `path` lives on: the longest mount point that contains it."""

    text = str(path)
    best: Mount | None = None
    for mount in mounts:
        prefix = mount.point.rstrip("/") + "/"
        if (text == mount.point or text.startswith(prefix) or mount.point == "/") and (
            best is None or len(mount.point) > len(best.point)
        ):
            best = mount
    return best


def _statvfs(point: str) -> Usage:
    stats = os.statvfs(point)
    return Usage(total=stats.f_blocks * stats.f_frsize, free=stats.f_bavail * stats.f_frsize)


def usage(point: str, measure: Callable[[str], Usage] = _statvfs, timeout: float = STATVFS_TIMEOUT) -> Usage | None:
    try:
        return _POOL.submit(measure, point).result(timeout=timeout)
    except (FutureTimeout, OSError):
        return None


def read_proc_mounts() -> str:
    try:
        return Path("/proc/self/mounts").read_text(encoding="utf-8")
    except OSError:
        return ""


def disks_and_mounts(
    components: dict[str, Path],
    read: Callable[[], str] = read_proc_mounts,
    measure: Callable[[str], Usage] = _statvfs,
) -> list[MountRow]:
    """Every real mount, its size and free space, and which of
    `components` (label → path) it holds."""

    mounts = parse_mounts(read())
    held: dict[str, list[str]] = {}
    for label, path in components.items():
        mount = holder(path.resolve(), mounts)
        if mount is not None:
            held.setdefault(mount.point, []).append(label)

    return [MountRow(mount, usage(mount.point, measure), tuple(held.get(mount.point, ()))) for mount in mounts]
