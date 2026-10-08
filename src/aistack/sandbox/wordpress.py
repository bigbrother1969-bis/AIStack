"""
The WordPress recipe (`ADR-0018` § 4): a `mariadb-dump` of the
database and a `tar czf` of `wp-content`, as
`/srv/scripts/backup-wordpress.sh` writes them on the reference host.

Restored with the images the live containers run, on the run's own
internal network: MariaDB loads the dump at its first start, WordPress
serves `wp-content` restored from the archive. Then checked from inside
the network — the tables are there, WordPress reads its own address
from them, the home page and the login page answer.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from aistack.sandbox.declaration import SandboxRecipe
from aistack.sandbox.compare import MARIADB, compare, compare_files, compare_tables, live_mount_source
from aistack.sandbox.run import SandboxRun, StepFailed

DATABASE = "wordpress"

# Fetches one path from the WordPress container itself, as the address
# it believes it has: status, Location, size, whether a login form is
# there. No curl needed: the image runs PHP.
_FETCH = r"""
$c = stream_context_create(["http" => ["ignore_errors" => true, "follow_location" => 0, "timeout" => 20,
  "header" => "Host: " . getenv("AISTACK_HOST") . "\r\nX-Forwarded-Proto: https\r\n"]]);
$b = @file_get_contents("http://127.0.0.1" . getenv("AISTACK_PATH"), false, $c);
if ($b === false || !isset($http_response_header[0])) { echo "ERR\n"; exit(1); }
$loc = "";
foreach ($http_response_header as $l) { if (stripos($l, "Location:") === 0) { $loc = trim(substr($l, 9)); } }
$p = explode(" ", $http_response_header[0]);
echo ($p[1] ?? "0"), "\n", $loc, "\n", strlen($b), "\n", (strpos($b, "user_login") !== false ? "login" : "-"), "\n";
"""


def newest(directory: Path, pattern: str) -> Path | None:
    """The newest file matching `pattern` — by name, which carries the
    backup's date and time, then by modification time."""

    found = [path for path in directory.glob(pattern) if path.is_file()]
    if not found:
        return None
    return max(found, key=lambda path: (path.name, path.stat().st_mtime))


def _stamp(path: Path, prefix: str) -> str:
    return path.name.removeprefix(prefix).split(".", 1)[0]


def _count_files(root: Path) -> int:
    total = 0
    for _, _, files in os.walk(root, onerror=lambda error: None):
        total += len(files)
    return total


def restore_wordpress(
    run: SandboxRun,
    recipe: SandboxRecipe,
    *,
    expansion: float,
    margin_gib: float,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Restore, check, time. Raises `StepFailed`; the caller tears down."""

    with run.step("backup files"):
        if not recipe.backup_dir.is_dir():
            raise StepFailed(f"no backup directory at {recipe.backup_dir}")
        dump = newest(recipe.backup_dir, recipe.database_dump)
        archive = newest(recipe.backup_dir, recipe.files_archive)
        if dump is None:
            raise StepFailed(f"no database dump `{recipe.database_dump}` in {recipe.backup_dir}")
        if archive is None:
            raise StepFailed(f"no files archive `{recipe.files_archive}` in {recipe.backup_dir}")
        run.facts["backup"] = {
            "database_dump": str(dump),
            "database_dump_bytes": dump.stat().st_size,
            "files_archive": str(archive),
            "files_archive_bytes": archive.stat().st_size,
            "same_night": _stamp(dump, "db-") == _stamp(archive, "wp-content-"),
        }
        if dump.stat().st_size == 0:
            raise StepFailed(f"the database dump {dump.name} is empty")

    with run.step("live images"):
        images = {}
        for role, container in (("database", recipe.live_database_container), ("web", recipe.live_web_container)):
            shown = run.docker("inspect", "--format", "{{.Image}} {{.Config.Image}}", container).stdout.split()
            if len(shown) < 2:
                raise StepFailed(f"cannot read the image of the live container {container}")
            images[role] = {"id": shown[0], "name": shown[1], "live_container": container}
        run.facts["images"] = images
    database_image = run.image_for(recipe.live_database_container, images["database"]["id"])
    web_image = run.image_for(recipe.live_web_container, images["web"]["id"])

    with run.step("room"):
        run.check_room((dump, archive), expansion, margin_gib)

    with run.step("isolation"):
        run.make_directory(web_image)
        run.create_network()

    run.mark_restore_started()
    with run.step("restore files"):
        run.docker(
            "run", "--rm", "--network", "none", *run.label_args(), "--entrypoint", "tar",
            "-v", f"{archive}:/backup/archive.tar.gz:ro", "-v", f"{run.directory}:/restore",
            web_image, "-xzf", "/backup/archive.tar.gz", "-C", "/restore",
            timeout=1800,
        )
    content = run.directory / "wp-content"
    files = _count_files(content) if content.is_dir() else 0
    run.check("files restored", files > 0, f"{files} file(s) in wp-content")
    run.check(
        "uploads restored", (content / "uploads").is_dir(), "wp-content/uploads present"
        if (content / "uploads").is_dir() else "no wp-content/uploads", required=False,
    )

    with run.step("start database"):
        (run.directory / "db").mkdir()
        env = run.write_env(".db.env", {"MARIADB_ROOT_PASSWORD": run.password, "MARIADB_DATABASE": DATABASE})
        run.docker(
            "run", "-d", "--name", run.name("db"), "--network", run.network, "--network-alias", "db",
            *run.label_args(), "--env-file", str(env),
            "-v", f"{run.directory / 'db'}:/var/lib/mysql",
            "-v", f"{dump}:/docker-entrypoint-initdb.d/restore.sql:ro",
            database_image,
        )

    def sql(query: str) -> str:
        return run.docker(
            "exec", run.name("db"), "sh", "-c",
            f'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb -uroot -h127.0.0.1 -N -B {DATABASE} -e "$1"',
            "sh", query, timeout=60,
        ).stdout.strip()

    with run.step("load database"):
        deadline = run.clock() + recipe.database_timeout_seconds
        while True:
            probe = run.docker_try(
                "exec", run.name("db"), "sh", "-c",
                'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb -uroot -h127.0.0.1 -N -B -e "SELECT 1"',
                timeout=30,
            )
            if probe.returncode == 0:
                break
            running = run.docker_try("inspect", "--format", "{{.State.Running}}", run.name("db")).stdout.strip()
            if running != "true":
                logs = run.docker_try("logs", "--tail", "5", run.name("db"))
                tail = (logs.stderr or logs.stdout).strip().splitlines()
                raise StepFailed("the database stopped while loading the dump" + (f": {tail[-1]}" if tail else ""))
            if run.clock() > deadline:
                raise StepFailed(f"the database did not answer within {recipe.database_timeout_seconds:g} s")
            sleep(2)

    tables = int(sql(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='{DATABASE}'") or 0)
    run.check("tables loaded", tables > 0, f"{tables} table(s)")
    options = [
        name for name in sql(
            f"SELECT table_name FROM information_schema.tables WHERE table_schema='{DATABASE}' "
            "AND table_name LIKE '%options'"
        ).splitlines() if name
    ]
    if not options:
        run.check("WordPress tables", False, "no options table")
        raise StepFailed("the dump holds no WordPress options table")
    prefix = sorted(options, key=len)[0].removesuffix("options")
    siteurl = sql(f"SELECT option_value FROM {prefix}options WHERE option_name='siteurl'")
    home = sql(f"SELECT option_value FROM {prefix}options WHERE option_name='home'") or siteurl
    run.check("site address", bool(siteurl), siteurl or "no siteurl option")
    users = sql(f"SELECT COUNT(*) FROM {prefix}users")
    posts = sql(f"SELECT COUNT(*) FROM {prefix}posts WHERE post_status='publish'")
    run.facts["database"] = {"tables": tables, "table_prefix": prefix, "siteurl": siteurl, "home": home,
                             "users": users, "published_posts": posts}

    with run.step("start WordPress"):
        env = run.write_env(".web.env", {
            "WORDPRESS_DB_HOST": "db",
            "WORDPRESS_DB_NAME": DATABASE,
            "WORDPRESS_DB_USER": "root",
            "WORDPRESS_DB_PASSWORD": run.password,
            "WORDPRESS_TABLE_PREFIX": prefix,
        })
        run.docker(
            "run", "-d", "--name", run.name("web"), "--network", run.network, *run.label_args(),
            "--env-file", str(env), "-v", f"{content}:/var/www/html/wp-content", web_image,
        )

    host = urlsplit(home).netloc or "localhost"

    def fetch(path: str) -> list[str]:
        result = run.docker_try(
            "exec", "-e", f"AISTACK_PATH={path}", "-e", f"AISTACK_HOST={host}",
            run.name("web"), "php", "-r", _FETCH, timeout=60,
        )
        return result.stdout.splitlines() if result.returncode == 0 else []

    with run.step("answer over HTTP"):
        deadline = run.clock() + recipe.web_timeout_seconds
        while not (answer := fetch("/")):
            if run.clock() > deadline:
                raise StepFailed(f"WordPress did not answer within {recipe.web_timeout_seconds:g} s")
            sleep(2)

    status, location = (answer + ["", ""])[:2]
    redirect_ok = status.startswith("3") and "install.php" not in location and (
        location.startswith(home.rstrip("/")) or location.startswith(siteurl.rstrip("/"))
    )
    run.check(
        "home page", status == "200" or redirect_ok,
        f"HTTP {status}" + (f" → {location}" if location else ""),
    )
    login = fetch("/wp-login.php")
    run.check(
        "login page", bool(login) and login[0] == "200" and login[3:4] == ["login"],
        f"HTTP {login[0]}" if login else "no answer", required=False,
    )
    if run.succeeded:
        run.restore_finished = run.clock()
    compare(run, [
        ("base", lambda: compare_tables(
            run, engine=MARIADB, sandbox_container=run.name("db"), sandbox_database=DATABASE,
            live_container=recipe.live_database_container,
        )),
        ("wp-content", lambda: compare_files(
            content, live_mount_source(run, recipe.live_web_container, "/var/www/html/wp-content"),
        )),
    ])
