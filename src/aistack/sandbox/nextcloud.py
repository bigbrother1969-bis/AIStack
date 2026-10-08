"""
The Nextcloud recipe (`ADR-0018` § 4): the nightly
`mariadb-dump --databases nextcloud` loaded into the image `nc_db`
runs, on the run's internal network, then read back — tables, users,
the file index.

Nextcloud's files have no backup on the reference host (measured
2026-10-08, `backup_strategy.yml` `nextcloud-files`): the run restores
the database only and its report says so. Starting Nextcloud itself
would need its live `config.php` and its secrets, which a sandbox never
reads.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from aistack.sandbox.databases import (
    live_image,
    mariadb_answers,
    mariadb_sql,
    start_mariadb,
    wait_until_loaded,
)
from aistack.sandbox.declaration import SandboxRecipe
from aistack.sandbox.compare import MARIADB, compare, compare_tables
from aistack.sandbox.run import SandboxRun, StepFailed
from aistack.sandbox.wordpress import newest

DATABASE = "nextcloud"


def restore_nextcloud(
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
        if recipe.not_backed_up:
            run.facts["not_backed_up"] = recipe.not_backed_up

    with run.step("live images"):
        image, _ = live_image(run, recipe.live_database_container, "database")

    with run.step("room"):
        run.check_room((dump,), recipe.expansion or expansion, margin_gib)

    with run.step("isolation"):
        run.make_directory(image)
        run.create_network()

    run.mark_restore_started()
    with run.step("start database"):
        start_mariadb(run, image, dump)
    with run.step("load database"):
        wait_until_loaded(run, lambda: mariadb_answers(run), recipe.database_timeout_seconds, sleep)

    tables = int(mariadb_sql(run, f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='{DATABASE}'") or 0)
    run.check("tables loaded", tables > 0, f"{tables} table(s)")
    found = [
        name for name in mariadb_sql(
            run, f"SELECT table_name FROM information_schema.tables WHERE table_schema='{DATABASE}' "
            "AND table_name LIKE '%appconfig'"
        ).splitlines() if name
    ]
    if not found:
        run.check("Nextcloud tables", False, "no appconfig table")
        raise StepFailed("the dump holds no Nextcloud appconfig table")
    prefix = sorted(found, key=len)[0].removesuffix("appconfig")
    installed_at = mariadb_sql(
        run, f"SELECT configvalue FROM {prefix}appconfig WHERE appid='core' AND configkey='installedat'", DATABASE
    )
    users = int(mariadb_sql(run, f"SELECT COUNT(*) FROM {prefix}users", DATABASE) or 0)
    files = int(mariadb_sql(run, f"SELECT COUNT(*) FROM {prefix}filecache", DATABASE) or 0)
    run.check("users", users > 0, f"{users} account(s)")
    run.check("file index", files > 0, f"{files} entr(y/ies) in {prefix}filecache")
    run.facts["database"] = {"tables": tables, "table_prefix": prefix, "users": users, "file_index": files,
                             "installed_at": installed_at}
    run.check(
        "files backed up", False,
        recipe.not_backed_up or "the files are not part of this test", required=False,
    )
    if run.succeeded:
        run.restore_finished = run.clock()
    compare(run, [
        ("base", lambda: compare_tables(
            run, engine=MARIADB, sandbox_container=run.name("db"), sandbox_database=DATABASE,
            live_container=recipe.live_database_container,
        )),
    ])
