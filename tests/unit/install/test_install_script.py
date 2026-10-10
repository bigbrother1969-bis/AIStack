"""`scripts/install.sh` (ADR-0023 § 4), run in `--dry-run`: it reads the
system, says every change it would make, and changes nothing."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "install.sh"

LMDE = 'PRETTY_NAME="LMDE 7 (Gigi)"\nID=linuxmint\nID_LIKE=debian\nVERSION_CODENAME=gigi\nDEBIAN_CODENAME=trixie\n'
MINT = 'PRETTY_NAME="Linux Mint 22"\nID=linuxmint\nID_LIKE="ubuntu debian"\nVERSION_CODENAME=wilma\nUBUNTU_CODENAME=noble\n'
FEDORA = 'PRETTY_NAME="Fedora Linux 42"\nID=fedora\nVERSION_CODENAME=""\n'


def dry_run(tmp_path: Path, os_release: str) -> subprocess.CompletedProcess[str]:
    release = tmp_path / "os-release"
    release.write_text(os_release, encoding="utf-8")
    return subprocess.run(
        ["bash", str(SCRIPT), "--dry-run", "--dir", str(tmp_path / "aistack")],
        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(tmp_path), "AISTACK_OS_RELEASE": str(release)},
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_on_lmde_it_says_every_step_and_changes_nothing(tmp_path: Path):
    result = dry_run(tmp_path, LMDE)

    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "dépôts debian (trixie)" in out
    for step in ("1. Le système", "2. Docker", "3. Le dossier", "4. Les prérequis", "5. Démarrer AIStack"):
        assert step in out
    for prerequisite in ("pocket-id", "gotify", "syncthing"):
        assert f"deploy/prerequisites/{prerequisite}/compose.yml" in out
    # On a host that already has Ollama and the model (GIGABYTE), there
    # is nothing to pull: the script says so instead.
    assert "ollama pull qwen2.5:3b" in out or "Ollama déjà installé" in out
    assert ":8186/setup" in out
    assert not (tmp_path / "aistack").exists()


def test_no_secret_is_ever_printed(tmp_path: Path):
    out = dry_run(tmp_path, LMDE).stdout
    assert "ENCRYPTION_KEY=" not in out and "GOTIFY_DEFAULTUSER_PASS=" not in out


def test_a_mint_host_takes_the_ubuntu_repository(tmp_path: Path):
    assert "dépôts ubuntu (noble)" in dry_run(tmp_path, MINT).stdout


def test_another_system_is_told_what_to_install_and_stops(tmp_path: Path):
    result = dry_run(tmp_path, FEDORA)
    assert result.returncode == 1
    assert "Docker Engine et le plugin Compose" in result.stderr


def test_shellcheck_finds_nothing():
    # From the `dev` extra (`shellcheck-py`), installed beside pytest.
    beside = Path(sys.executable).parent / "shellcheck"
    shellcheck = shutil.which("shellcheck") or (str(beside) if beside.exists() else None)
    assert shellcheck, 'shellcheck missing: python -m pip install -e ".[dev]"'
    result = subprocess.run([shellcheck, str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


def test_the_shipped_prerequisites_are_the_ones_the_script_installs():
    shipped = {path.parent.name for path in (ROOT / "deploy" / "prerequisites").glob("*/compose.yml")}
    assert shipped == {"pocket-id", "gotify", "syncthing"}


def test_it_leaves_the_assistant_its_answers_and_the_address_with_the_token(tmp_path: Path):
    # ADR-0023 § 5: install.env (never a secret) and the token that opens /setup.
    out = dry_run(tmp_path, LMDE).stdout

    assert "data/setup/install.env (mode 600)" in out
    assert "data/setup/token (mode 600)" in out
    assert ":8186/setup/open?token=JETON" in out
    assert "aistack.cli.setup_token" in out
