"""The maintenance page (`deploy/maintenance/`, `scripts/maintenance_page.sh`):
shown while Docker is stopped for the weekly full backup. The script runs
here against fake `systemctl`, `nginx`, `ss` and `curl`, under a temporary
root, and the tests read the calls it made."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "maintenance_page.sh"
HTML = ROOT / "deploy" / "maintenance" / "maintenance.html"
CONF = ROOT / "deploy" / "maintenance" / "nginx.conf"
UNIT = ROOT / "deploy" / "systemd" / "aistack-maintenance.service"

FAKES = {
    "systemctl": 'echo "systemctl $*" >> "$CALLS"\n'
    'if [ "$1" = is-active ]; then [ -f "$ACTIVE" ]; exit; fi\n'
    'case "$*" in "start aistack-maintenance.service") touch "$ACTIVE";; "stop aistack-maintenance.service") rm -f "$ACTIVE";; esac\n',
    "nginx": 'echo "nginx $*" >> "$CALLS"\n',
    "apt-get": 'echo "apt-get $*" >> "$CALLS"\n',
    "ss": '[ -f "$BUSY" ] && echo "LISTEN 0 4096 0.0.0.0:80 0.0.0.0:*"\nexit 0\n',
    "curl": 'echo "${FAKE_HTTP:-503}"\n',
    "sleep": "exit 0\n",
}


def environment(tmp_path: Path, *, busy: bool = False) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, body in FAKES.items():
        path = bin_dir / name
        path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    busy_file = tmp_path / "busy"
    if busy:
        busy_file.write_text("")
    return {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "AISTACK_MAINTENANCE_ROOT": str(tmp_path / "root"),
        "AISTACK_MAINTENANCE_WAIT": "0",
        "CALLS": str(tmp_path / "calls"),
        "ACTIVE": str(tmp_path / "active"),
        "BUSY": str(busy_file),
    }


def run(tmp_path: Path, *args: str, busy: bool = False, extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = environment(tmp_path, busy=busy) | (extra or {})
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=60)


def calls(tmp_path: Path) -> list[str]:
    path = tmp_path / "calls"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def installed(tmp_path: Path, *args: str) -> None:
    result = run(tmp_path, "install", "--yes", *args)
    assert result.returncode == 0, result.stderr
    (tmp_path / "calls").unlink(missing_ok=True)


def test_the_page_is_self_contained_and_says_it_in_both_languages():
    html = HTML.read_text(encoding="utf-8")
    assert "Maintenance en cours" in html and "Maintenance in progress" in html
    # Nothing to fetch: the page must show while the network services are down.
    assert not re.search(r'(?:src|href)="https?://', html)
    assert 'http-equiv="refresh"' in html


def test_nginx_answers_503_with_the_page_and_a_retry_hint():
    conf = CONF.read_text(encoding="utf-8")
    assert "return 503;" in conf and "error_page 503 /maintenance.html;" in conf
    assert "Retry-After" in conf and "internal;" in conf


def test_the_unit_is_never_started_at_boot():
    unit = UNIT.read_text(encoding="utf-8")
    assert "\n[Install]" not in unit
    assert "nginx -c /etc/aistack-maintenance/nginx.conf" in unit


def test_install_dry_run_changes_nothing(tmp_path: Path):
    result = run(tmp_path, "install", "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "[simulation]" in result.stdout
    assert not (tmp_path / "root").exists()
    assert not calls(tmp_path)


def test_install_puts_the_three_files_and_enables_nothing(tmp_path: Path):
    result = run(tmp_path, "install", "--yes")
    assert result.returncode == 0, result.stderr
    root = tmp_path / "root"
    assert (root / "usr/share/aistack-maintenance/maintenance.html").is_file()
    assert (root / "etc/systemd/system/aistack-maintenance.service").is_file()
    conf = (root / "etc/aistack-maintenance/nginx.conf").read_text(encoding="utf-8")
    assert not re.search(r"^#TLS#", conf, re.M) and "listen 443" not in conf and "listen 80 default_server;" in conf
    assert not any(" enable" in call for call in calls(tmp_path))


def test_without_ipv6_the_listen_lines_for_it_are_left_out(tmp_path: Path):
    no_ipv6 = tmp_path / "absent"
    result = run(tmp_path, "install", "--yes", extra={"AISTACK_MAINTENANCE_IF_INET6": str(no_ipv6)})
    assert result.returncode == 0, result.stderr
    conf = (tmp_path / "root/etc/aistack-maintenance/nginx.conf").read_text(encoding="utf-8")
    assert "[::]" not in conf and "listen 80 default_server;" in conf


def test_with_ipv6_the_listen_lines_for_it_stay(tmp_path: Path):
    present = tmp_path / "if_inet6"
    present.write_text("")
    run(tmp_path, "install", "--yes", extra={"AISTACK_MAINTENANCE_IF_INET6": str(present)})
    conf = (tmp_path / "root/etc/aistack-maintenance/nginx.conf").read_text(encoding="utf-8")
    assert "listen [::]:80 default_server;" in conf


def test_install_with_tls_listens_on_443_with_the_given_certificate(tmp_path: Path):
    cert, key = tmp_path / "c.pem", tmp_path / "k.pem"
    cert.write_text("x")
    key.write_text("x")
    installed(tmp_path, "--tls", str(cert), str(key))
    conf = (tmp_path / "root/etc/aistack-maintenance/nginx.conf").read_text(encoding="utf-8")
    assert "listen 443 ssl default_server;" in conf
    assert f"ssl_certificate     {cert};" in conf
    assert not re.search(r"^#TLS#|@TLS_", conf, re.M)


def test_a_second_install_keeps_a_dated_copy_of_what_it_replaces(tmp_path: Path):
    installed(tmp_path)
    run(tmp_path, "install", "--yes")
    names = [p.name for p in (tmp_path / "root/etc/aistack-maintenance").iterdir()]
    assert any(re.fullmatch(r"nginx\.conf\.avant-\d{8}-\d{6}", n) for n in names)


def test_uninstall_removes_what_install_created(tmp_path: Path):
    installed(tmp_path)
    result = run(tmp_path, "uninstall", "--yes")
    assert result.returncode == 0, result.stderr
    root = tmp_path / "root"
    assert not (root / "etc/aistack-maintenance").exists()
    assert not (root / "etc/systemd/system/aistack-maintenance.service").exists()
    assert not (root / "usr/share/aistack-maintenance").exists()


def test_on_waits_for_port_80_and_gives_up_with_a_clear_message(tmp_path: Path):
    installed(tmp_path)
    result = run(tmp_path, "on", busy=True)
    assert result.returncode == 1
    assert "port 80" in result.stderr
    assert not any("start aistack-maintenance" in call for call in calls(tmp_path))


def test_on_checks_that_the_page_really_answers_503(tmp_path: Path):
    installed(tmp_path)
    assert run(tmp_path, "on").returncode == 0
    wrong = run(tmp_path, "on", extra={"FAKE_HTTP": "200"})
    assert wrong.returncode == 1 and "503" in wrong.stderr


def test_run_stops_docker_shows_the_page_runs_then_restores(tmp_path: Path):
    installed(tmp_path)
    result = run(tmp_path, "run", "--", "sh", "-c", f'echo "COMMAND" >> "{tmp_path / "calls"}"')
    assert result.returncode == 0, result.stderr
    assert calls(tmp_path) == [
        "systemctl stop docker.service docker.socket",
        "systemctl start aistack-maintenance.service",
        "COMMAND",
        "systemctl stop aistack-maintenance.service",
        "systemctl start docker.service",
    ]


def test_run_restores_docker_and_returns_the_code_when_the_command_fails(tmp_path: Path):
    installed(tmp_path)
    result = run(tmp_path, "run", "--", "sh", "-c", "exit 7")
    assert result.returncode == 7
    assert calls(tmp_path)[-2:] == ["systemctl stop aistack-maintenance.service", "systemctl start docker.service"]


def test_run_refuses_when_the_page_is_not_installed_and_stops_nothing(tmp_path: Path):
    result = run(tmp_path, "run", "--", "true")
    assert result.returncode == 1
    assert "pas installée" in result.stderr
    assert not calls(tmp_path)


def test_run_dry_run_stops_nothing(tmp_path: Path):
    result = run(tmp_path, "run", "--dry-run", "--", "rear", "mkbackup")
    assert result.returncode == 0, result.stderr
    assert "Docker redémarré" in result.stdout and not calls(tmp_path)


def test_shellcheck_finds_nothing():
    beside = Path(sys.executable).parent / "shellcheck"
    shellcheck = shutil.which("shellcheck") or (str(beside) if beside.exists() else None)
    assert shellcheck, 'shellcheck missing: python -m pip install -e ".[dev]"'
    result = subprocess.run([shellcheck, str(SCRIPT)], capture_output=True, text=True, timeout=60, env=os.environ)
    assert result.returncode == 0, result.stdout
