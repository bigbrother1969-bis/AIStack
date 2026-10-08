"""
The Immich recipe (`ADR-0018` § 4): the nightly `pg_dump` of the
`immich` database loaded into the image `immich_postgres` runs (with
its vector extensions), on the run's internal network, then read back
— tables, assets, users.

Then a few photos of the external library the restored database names
are taken back from the Deja Dup backup (duplicity, on the host) and
their SHA-1 compared with the checksum the database holds: the proof
that the database and the files backed up agree. Uploaded photos have
no backup on the reference host (measured 2026-10-08,
`backup_strategy.yml` `immich-uploads`): the report counts them and
says so.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable
from pathlib import Path

from aistack.sandbox.databases import (
    live_image,
    postgres_answers,
    postgres_sql,
    start_postgres,
    wait_until_loaded,
)
from aistack.sandbox.declaration import FileSample, SandboxRecipe
from aistack.sandbox.run import SandboxRun, StepFailed
from aistack.sandbox.wordpress import newest

DATABASE = "immich"


def _table(run: SandboxRun, *names: str) -> str:
    listed = ", ".join(f"'{name}'" for name in names)
    found = postgres_sql(
        run, f"SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
        f"AND table_name IN ({listed}) ORDER BY table_name", DATABASE,
    ).splitlines()
    if not found:
        raise StepFailed(f"the dump holds none of the tables {', '.join(names)}")
    return found[0]


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()  # noqa: S324 - Immich's own checksum, compared, not trusted for security
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _differs(target: Path, original: str, checksum: str, size: int) -> str:
    """'' when the restored file is the one the database names, else
    how it differs.

    Immich hashes an uploaded photo's content; for an external-library
    photo it stores the SHA-1 of `path:<originalPath>` instead, so as
    not to read the whole library at every scan (GIGABYTE, 2026-10-08:
    all three sampled photos "differed" against a content hash). Such a
    checksum proves nothing about the content: the file's size is then
    compared with the one Immich read from it (EXIF table).
    """

    if not target.is_file() or target.stat().st_size == 0:
        return "restored file is empty or missing"
    path_hash = hashlib.sha1(f"path:{original}".encode()).hexdigest()  # noqa: S324
    if checksum == path_hash:
        if size < 0:
            return "no size recorded by Immich to compare with"
        if target.stat().st_size != size:
            return f"size {target.stat().st_size} bytes, Immich recorded {size}"
        return ""
    return "" if _sha1(target) == checksum else "content checksum differs"


def _restore_one(run: SandboxRun, sample: FileSample, relative: str, target: Path) -> str:
    """Take one file back from the duplicity backup; '' when it worked,
    else why not."""

    cache = os.path.expanduser(sample.archive_dir) if sample.archive_dir else str(run.directory / "duplicity-cache")
    common = ["--no-encryption", "--archive-dir", cache]
    if sample.archive_dir and sample.archive_name:
        # The cache Deja Dup keeps for this backup, by its own name: the
        # default name (a hash of the URL) differs, and duplicity would
        # rebuild a second cache beside it (GIGABYTE, 2026-10-08).
        common += ["--name", sample.archive_name]
    source = f"file://{sample.duplicity_target}"
    result = run.host(
        ["duplicity", "restore", *common, "--path-to-restore", relative, source, str(target)], 1800
    )
    if result.returncode != 0 and "path-to-restore" in (result.stderr + result.stdout):
        # duplicity before 2.0 names the option differently.
        result = run.host(
            ["duplicity", "restore", *common, "--file-to-restore", relative, source, str(target)], 1800
        )
    if result.returncode != 0:
        lines = (result.stderr or result.stdout).strip().splitlines()
        return lines[-1] if lines else f"duplicity exited with {result.returncode}"
    return ""


def restore_immich(
    run: SandboxRun,
    recipe: SandboxRecipe,
    *,
    expansion: float,
    margin_gib: float,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    with run.step("backup files"):
        dump = newest(recipe.backup_dir, recipe.database_dump) if recipe.backup_dir.is_dir() else None
        if dump is None:
            raise StepFailed(f"no database dump `{recipe.database_dump}` in {recipe.backup_dir}")
        run.facts["backup"] = {"database_dump": str(dump), "database_dump_bytes": dump.stat().st_size}

    with run.step("live images"):
        image, command = live_image(run, recipe.live_database_container, "database")

    with run.step("room"):
        run.check_room((dump,), recipe.expansion or expansion, margin_gib)

    with run.step("isolation"):
        run.make_directory(image)
        run.create_network()

    run.mark_restore_started()
    with run.step("start database"):
        start_postgres(run, image, command, dump, DATABASE)
    with run.step("load database"):
        wait_until_loaded(run, lambda: postgres_answers(run, DATABASE), recipe.database_timeout_seconds, sleep)

    tables = int(postgres_sql(
        run, "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'", DATABASE
    ) or 0)
    run.check("tables loaded", tables > 0, f"{tables} table(s)")
    asset = _table(run, "asset", "assets")
    user = _table(run, "user", "users")
    assets = int(postgres_sql(run, f'SELECT COUNT(*) FROM "{asset}" WHERE "deletedAt" IS NULL', DATABASE) or 0)
    users = int(postgres_sql(run, f'SELECT COUNT(*) FROM "{user}"', DATABASE) or 0)
    run.check("assets", assets > 0, f"{assets} asset(s)")
    run.check("users", users > 0, f"{users} account(s)")
    run.facts["database"] = {"tables": tables, "assets": assets, "users": users}

    sample = recipe.file_sample
    if sample is not None:
        prefix = sample.live_prefix.replace("'", "''")
        external = int(postgres_sql(
            run, f'SELECT COUNT(*) FROM "{asset}" WHERE "deletedAt" IS NULL AND "originalPath" LIKE \'{prefix}%\'',
            DATABASE,
        ) or 0)
        run.facts["database"]["external_library_assets"] = external
        run.facts["database"]["uploaded_assets"] = assets - external
        if recipe.not_backed_up:
            run.facts["not_backed_up"] = f"{recipe.not_backed_up} ({assets - external} asset(s))"

        with run.step("file sample"):
            exif = _table(run, "asset_exif", "exif")
            rows = [
                line.split("|", 2) for line in postgres_sql(
                    run,
                    f'SELECT a."originalPath", encode(a.checksum, \'hex\'), coalesce(e."fileSizeInByte", -1) '
                    f'FROM "{asset}" a LEFT JOIN "{exif}" e ON e."assetId" = a.id '
                    f'WHERE a."deletedAt" IS NULL AND a."originalPath" LIKE \'{prefix}%\' '
                    f'AND a."createdAt" < now() - interval \'{sample.older_than_days} days\' '
                    f"ORDER BY random() LIMIT {sample.count}",
                    DATABASE,
                ).splitlines() if line.count("|") == 2
            ]
            (run.directory / "sample").mkdir()
            matched = 0
            details = []
            for index, (original, checksum, size) in enumerate(rows):
                host_path = sample.host_prefix.rstrip("/") + "/" + original[len(sample.live_prefix):].lstrip("/")
                relative = host_path.lstrip("/")
                target = run.directory / "sample" / f"{index}-{Path(original).name}"
                run.progress(f"    photo {index + 1}/{len(rows)} : {Path(original).name}")
                problem = _restore_one(run, sample, relative, target)
                if problem:
                    details.append(f"{Path(original).name}: {problem}")
                else:
                    difference = _differs(target, original, checksum, int(size))
                    if difference:
                        details.append(f"{Path(original).name}: {difference}")
                    else:
                        matched += 1
        run.check(
            "photos from Deja Dup match the database", bool(rows) and matched == len(rows),
            f"{matched}/{len(rows)} photo(s) restored and matching the database"
            + (" — " + "; ".join(details) if details else ""),
            required=external > 0,
        )
    run.check(
        "uploads backed up", False,
        run.facts.get("not_backed_up") or recipe.not_backed_up or "not part of this test", required=False,
    )
    if run.succeeded:
        run.restore_finished = run.clock()
