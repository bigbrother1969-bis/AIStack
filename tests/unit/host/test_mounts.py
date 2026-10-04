"""`aistack.host.mounts`: the real mounts of a `/proc/mounts`, and where AIStack's components live."""

from __future__ import annotations

import time
from pathlib import Path

from aistack.host.mounts import Usage, disks_and_mounts, holder, parse_mounts, usage

PROC = """sysfs /sys sysfs rw,nosuid 0 0
proc /proc proc rw 0 0
/dev/sda2 / ext4 rw,relatime 0 0
tmpfs /run tmpfs rw 0 0
/dev/sdb1 /media/BACKUP ext4 rw 0 0
/dev/sdc1 /media/Tech\\040Data ext4 ro,relatime 0 0
nas:/volume1/music /mnt/music nfs4 rw 0 0
overlay /var/lib/docker/overlay2/abc/merged overlay rw 0 0
/dev/sda2 /var/lib/docker/plugins ext4 rw 0 0
"""


def test_only_real_mounts_are_kept_with_their_access():
    mounts = parse_mounts(PROC)

    assert [m.point for m in mounts] == ["/", "/media/BACKUP", "/media/Tech Data", "/mnt/music"]
    assert next(m for m in mounts if m.point == "/media/Tech Data").read_only
    assert next(m for m in mounts if m.point == "/mnt/music").network


def test_a_path_lives_on_the_longest_mount_point_holding_it():
    mounts = parse_mounts(PROC)

    assert holder(Path("/srv/aistack/AIStack"), mounts).point == "/"
    assert holder(Path("/media/BACKUP/nextcloud"), mounts).point == "/media/BACKUP"
    assert holder(Path("/media/BACKUPS"), mounts).point == "/"


def test_each_component_is_placed_and_sizes_are_measured():
    rows = disks_and_mounts(
        {"code": Path("/srv/aistack/AIStack"), "graph": Path("/media/BACKUP/graph")},
        read=lambda: PROC,
        measure=lambda point: Usage(total=1000, free=250),
    )

    by_point = {row.mount.point: row for row in rows}
    assert by_point["/"].components == ("code",)
    assert by_point["/media/BACKUP"].components == ("graph",)
    assert by_point["/mnt/music"].usage == Usage(1000, 250)


def test_a_mount_that_does_not_answer_is_not_waited_on():
    def hung(point: str) -> Usage:
        time.sleep(1)
        return Usage(1, 1)

    started = time.monotonic()
    assert usage("/mnt/music", hung, timeout=0.1) is None
    assert time.monotonic() - started < 0.5
