"""
Database restores shared by the recipes whose backup is a SQL dump
(`ADR-0018` § 4): Nextcloud (MariaDB) and Immich (PostgreSQL).

The dump is mounted into the database container's
`/docker-entrypoint-initdb.d/`, so the image loads it at its first
start — the way both official images restore a dump, compressed or
not. The run waits for the server to answer over TCP: during its
initialisation each image listens on its socket only, so a TCP answer
means the dump is loaded.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from aistack.sandbox.run import SandboxRun, StepFailed


def live_image(run: SandboxRun, container: str, role: str) -> tuple[str, list[str]]:
    """The live container's image id and command — what the sandbox
    reruns. Nothing else is read from it."""

    shown = run.docker("inspect", "--format", "{{.Image}} {{.Config.Image}}", container).stdout.split()
    if len(shown) < 2:
        raise StepFailed(f"cannot read the image of the live container {container}")
    command_json = run.docker("inspect", "--format", "{{json .Config.Cmd}}", container).stdout.strip()
    command = json.loads(command_json) if command_json and command_json != "null" else []
    run.facts.setdefault("images", {})[role] = {"id": shown[0], "name": shown[1], "live_container": container}
    return run.image_for(container, shown[0]), [str(part) for part in command]


def _init_name(dump: Path) -> str:
    return "restore.sql.gz" if dump.name.endswith(".gz") else "restore.sql"


def start_mariadb(run: SandboxRun, image: str, dump: Path, database: str = "") -> None:
    (run.directory / "db").mkdir()
    values = {"MARIADB_ROOT_PASSWORD": run.password}
    if database:
        values["MARIADB_DATABASE"] = database
    env = run.write_env(".db.env", values)
    run.docker(
        "run", "-d", "--name", run.name("db"), "--network", run.network, "--network-alias", "db",
        *run.label_args(), "--env-file", str(env),
        "-v", f"{run.directory / 'db'}:/var/lib/mysql",
        "-v", f"{dump}:/docker-entrypoint-initdb.d/{_init_name(dump)}:ro",
        image,
    )


def mariadb_sql(run: SandboxRun, query: str, database: str = "") -> str:
    target = f" {database}" if database else ""
    return run.docker(
        "exec", run.name("db"), "sh", "-c",
        f'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb -uroot -h127.0.0.1 -N -B{target} -e "$1"',
        "sh", query, timeout=120,
    ).stdout.strip()


def start_postgres(run: SandboxRun, image: str, command: list[str], dump: Path, database: str) -> None:
    (run.directory / "pg").mkdir()
    env = run.write_env(".db.env", {
        "POSTGRES_PASSWORD": run.password, "POSTGRES_USER": "postgres", "POSTGRES_DB": database,
    })
    run.docker(
        "run", "-d", "--name", run.name("db"), "--network", run.network, "--network-alias", "db",
        *run.label_args(), "--env-file", str(env),
        "-v", f"{run.directory / 'pg'}:/var/lib/postgresql/data",
        "-v", f"{dump}:/docker-entrypoint-initdb.d/{_init_name(dump)}:ro",
        image, *command,
    )


def postgres_sql(run: SandboxRun, query: str, database: str) -> str:
    return run.docker(
        "exec", run.name("db"), "sh", "-c",
        f'PGPASSWORD="$POSTGRES_PASSWORD" exec psql -h 127.0.0.1 -U postgres -d {database}'
        ' -v ON_ERROR_STOP=1 -tA -F "|" -c "$1"',
        "sh", query, timeout=300,
    ).stdout.strip()


def wait_until_loaded(
    run: SandboxRun,
    probe: Callable[[], bool],
    timeout: float,
    sleep: Callable[[float], None],
) -> None:
    deadline = run.clock() + timeout
    while not probe():
        running = run.docker_try("inspect", "--format", "{{.State.Running}}", run.name("db")).stdout.strip()
        if running != "true":
            logs = run.docker_try("logs", "--tail", "5", run.name("db"))
            tail = (logs.stderr or logs.stdout).strip().splitlines()
            raise StepFailed("the database stopped while loading the dump" + (f": {tail[-1]}" if tail else ""))
        if run.clock() > deadline:
            raise StepFailed(f"the database did not answer within {timeout:g} s")
        sleep(5)


def mariadb_answers(run: SandboxRun) -> bool:
    return run.docker_try(
        "exec", run.name("db"), "sh", "-c",
        'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb -uroot -h127.0.0.1 -N -B -e "SELECT 1"',
        timeout=30,
    ).returncode == 0


def postgres_answers(run: SandboxRun, database: str) -> bool:
    return run.docker_try(
        "exec", run.name("db"), "sh", "-c",
        f'PGPASSWORD="$POSTGRES_PASSWORD" exec psql -h 127.0.0.1 -U postgres -d {database} -tAc "SELECT 1"',
        timeout=30,
    ).returncode == 0
