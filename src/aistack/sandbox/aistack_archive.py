"""
The AIStack recipe (`ADR-0018` § 4): AIStack's own nightly archive
(`scripts/backup_aistack.sh`) restored with the image the live web
container runs — what `scripts/restore_aistack.sh` does by hand, run
the same way every time.

Checked as the hand test was: the session database's integrity, every
Explication readable, the history streams and declarations present;
then the Time Machine graph — left out of the archive — rebuilt from
the restored files, and the web application started on them, on the
run's internal network, answering with the console it rendered.

The archive's environment files hold the live secrets: they are
restored (the archive is whole or it is not) and counted, never given
to a sandbox container. Without them, sign-in is unavailable in the
sandbox — the console, which needs none, is what is checked.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable

from aistack.sandbox.declaration import SandboxRecipe
from aistack.sandbox.compare import compare, compare_files, live_mount_source
from aistack.sandbox.run import SandboxRun, StepFailed
from aistack.sandbox.wordpress import newest

_EXTRACT = (
    "tar -xzf /backup/archive.tar.gz -C /restore"
    " && if [ -f /restore/sessions.sqlite3 ]; then"
    " mkdir -p /restore/data/web && mv /restore/sessions.sqlite3 /restore/data/web/sessions.sqlite3; fi"
)

# What `scripts/restore_aistack.sh` checks, as one JSON line.
_INSPECT = r"""
import json, sqlite3
from pathlib import Path
t = Path("/restore"); d = t / "data"; out = {}
s = d / "web" / "sessions.sqlite3"
out["sessions"] = sqlite3.connect(f"file:{s}?mode=ro", uri=True).execute("PRAGMA integrity_check").fetchone()[0] if s.is_file() else "absent"
ex = list((d / "explications").rglob("*.json")) if (d / "explications").is_dir() else []
bad = 0
for p in ex:
    try:
        json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        bad += 1
out["explications"] = len(ex); out["explications_unreadable"] = bad
h = d / "history"
out["history_streams"] = len([c for c in h.iterdir() if c.is_dir()]) if h.is_dir() else 0
out["declarations"] = len(list((t / "config").glob("*.yml"))) if (t / "config").is_dir() else 0
out["environment_files"] = len(list((t / "env").iterdir())) if (t / "env").is_dir() else 0
m = t / "MANIFEST"
out["manifest"] = dict((k.strip(), v.strip()) for k, v in (l.split(":", 1) for l in m.read_text(encoding="utf-8").splitlines() if ":" in l)) if m.is_file() else {}
print(json.dumps(out))
"""

# One page of the sandboxed web application, from inside its container.
_FETCH = r"""
import os, urllib.error, urllib.request
from aistack.web.server import INSTANCE_CONFIG, listeners_from
port = listeners_from(INSTANCE_CONFIG).lan_port
class Stay(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
try:
    answer = urllib.request.build_opener(Stay).open(f"http://127.0.0.1:{port}{os.environ['AISTACK_PATH']}", timeout=10)
    print(answer.status)
except urllib.error.HTTPError as error:
    print(error.code)
"""


def restore_aistack(
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
        archive = newest(recipe.backup_dir, recipe.files_archive)
        if archive is None:
            raise StepFailed(f"no archive `{recipe.files_archive}` in {recipe.backup_dir}")
        run.facts["backup"] = {"files_archive": str(archive), "files_archive_bytes": archive.stat().st_size}

    with run.step("live images"):
        shown = run.docker("inspect", "--format", "{{.Image}} {{.Config.Image}}", recipe.live_web_container).stdout.split()
        if len(shown) < 2:
            raise StepFailed(f"cannot read the image of the live container {recipe.live_web_container}")
        run.facts["images"] = {"web": {"id": shown[0], "name": shown[1], "live_container": recipe.live_web_container}}
    image = run.image_for(recipe.live_web_container, shown[0])
    # The account the live installation runs as: the restored files
    # belong to it, as they do on the host.
    user = f"{os.getuid()}:{os.getgid()}"

    with run.step("room"):
        run.check_room((archive,), expansion, margin_gib)

    with run.step("isolation"):
        run.make_directory(image)
        run.create_network()

    run.mark_restore_started()
    with run.step("restore files"):
        run.docker(
            "run", "--rm", "--network", "none", "--user", user, *run.label_args(), "--entrypoint", "sh",
            "-v", f"{archive}:/backup/archive.tar.gz:ro", "-v", f"{run.directory}:/restore",
            image, "-c", _EXTRACT, timeout=1800,
        )

    with run.step("inspect"):
        shown_json = run.docker(
            "run", "--rm", "--network", "none", "--user", user, *run.label_args(), "--entrypoint", "python",
            "-v", f"{run.directory}:/restore:ro", image, "-c", _INSPECT, timeout=600,
        ).stdout.strip().splitlines()
        found = json.loads(shown_json[-1]) if shown_json else {}
    manifest = found.get("manifest") or {}
    run.facts["archive"] = {key: manifest[key] for key in ("created", "host", "commit", "image_version") if key in manifest}
    run.facts["restored"] = {key: found.get(key) for key in (
        "sessions", "explications", "explications_unreadable", "history_streams", "declarations", "environment_files"
    )}
    run.check("archive manifest", bool(manifest), f"created {manifest.get('created', '?')}" if manifest else "no MANIFEST")
    sessions = str(found.get("sessions", "absent"))
    run.check("session database", sessions in ("ok", "absent"), sessions)
    explications, unreadable = int(found.get("explications") or 0), int(found.get("explications_unreadable") or 0)
    run.check("explications readable", unreadable == 0, f"{explications} file(s), {unreadable} unreadable")
    streams = int(found.get("history_streams") or 0)
    run.check("history restored", streams > 0, f"{streams} stream(s)")
    declarations = int(found.get("declarations") or 0)
    run.check("declarations restored", declarations > 0, f"{declarations} file(s)")
    run.check(
        "environment files restored", int(found.get("environment_files") or 0) > 0,
        f"{found.get('environment_files') or 0} file(s), not given to the sandbox", required=False,
    )

    data, config = run.directory / "data", run.directory / "config"
    with run.step("rebuild Time Machine graph"):
        run.docker(
            "run", "--rm", "--network", "none", "--user", user, *run.label_args(),
            "-v", f"{data}:/app/reports/generated", "-v", f"{config}:/config",
            image, "python", "-m", "aistack.cli.timemachine_rebuild", timeout=1800,
        )
    graph = data / "timemachine" / "graph"
    run.check("Time Machine graph rebuilt", graph.exists(), "graph present" if graph.exists() else "no graph")

    with run.step("start AIStack"):
        run.docker(
            "run", "-d", "--name", run.name("web"), "--network", run.network, "--user", user,
            *run.label_args(), "-v", f"{data}:/app/reports/generated", "-v", f"{config}:/config",
            image, "web",
        )

    def fetch(path: str) -> str:
        result = run.docker_try(
            "exec", "-e", f"AISTACK_PATH={path}", run.name("web"), "python", "-c", _FETCH, timeout=30,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    with run.step("answer over HTTP"):
        deadline = run.clock() + recipe.web_timeout_seconds
        while not (console := fetch("/console.html")):
            running = run.docker_try("inspect", "--format", "{{.State.Running}}", run.name("web")).stdout.strip()
            if running != "true":
                logs = run.docker_try("logs", "--tail", "5", run.name("web"))
                tail = (logs.stderr or logs.stdout).strip().splitlines()
                raise StepFailed("AIStack stopped at start" + (f": {tail[-1]}" if tail else ""))
            if run.clock() > deadline:
                raise StepFailed(f"AIStack did not answer within {recipe.web_timeout_seconds:g} s")
            sleep(2)

    run.check("console", console == "200", f"HTTP {console}")
    health = fetch("/health.html")
    run.check("signed-in pages guarded", health in ("302", "303", "307"), f"HTTP {health or 'none'}", required=False)
    if run.succeeded:
        run.restore_finished = run.clock()
    compare(run, [
        ("données", lambda: compare_files(
            data, live_mount_source(run, recipe.live_web_container, "/app/reports/generated"),
        )),
    ])
