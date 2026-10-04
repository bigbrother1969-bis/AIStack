"""`aistack.cli.explications_admin` refuses outside the development phase (ADR-0016)."""

from __future__ import annotations

from pathlib import Path

from aistack.cli.explications_admin import main
from aistack.explications.human import Person, versions, write


def config(tmp_path: Path, phase: str | None) -> Path:
    path = tmp_path / "instance_config.yml"
    text = "lan_hostname: GIGABYTE\nservice_ports:\n  console: 8183\n"
    if phase:
        text += f"phase: {phase}\n"
    path.write_text(text, encoding="utf-8")
    return path


def test_purge_runs_in_development(tmp_path: Path, capsys):
    out = tmp_path / "explications"
    write("wordpress", "Test de développement", Person("person:x", "X"), out, expected=0)

    assert main(["purge", "wordpress"], config(tmp_path, "development"), out) == 0

    assert versions("wordpress", out) == []
    assert "1 version(s) deleted" in capsys.readouterr().out


def test_nothing_runs_in_production_or_when_the_phase_is_not_said(tmp_path: Path):
    out = tmp_path / "explications"
    write("wordpress", "Kept.", Person("person:x", "X"), out, expected=0)

    assert main(["purge", "wordpress"], config(tmp_path, "production"), out) == 1
    assert main(["validate-declared"], config(tmp_path, None), out) == 1
    assert len(versions("wordpress", out)) == 1
