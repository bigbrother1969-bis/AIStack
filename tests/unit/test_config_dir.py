"""`aistack.config` and `config_init` (ADR-0017 § 1): a declaration in the
configuration directory replaces the shipped one, file by file."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

from aistack.cli.config_init import init
from aistack.config import CONFIG_DIR_ENV, configured, shipped_definitions

SHIPPED = Path("/package/instance/definitions/instance_config.yml")


def test_without_a_directory_the_shipped_declaration_is_read(monkeypatch):
    monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)

    assert configured(SHIPPED) == SHIPPED


def test_a_file_in_the_directory_replaces_the_shipped_one_and_only_that_one(monkeypatch, tmp_path: Path):
    (tmp_path / "instance_config.yml").write_text("lan_hostname: OTHER\n", encoding="utf-8")
    monkeypatch.setenv(CONFIG_DIR_ENV, str(tmp_path))

    assert configured(SHIPPED) == tmp_path / "instance_config.yml"
    other = Path("/package/pra/definitions/pra_tests.yml")
    assert configured(other) == other


def test_every_shipped_declaration_has_a_distinct_name():
    names = [path.name for path in shipped_definitions()]

    assert len(names) == len(set(names)) >= 18


def test_init_copies_what_is_missing_and_never_overwrites(tmp_path: Path):
    (tmp_path / "instance_config.yml").write_text("mine\n", encoding="utf-8")

    copied, kept = init(tmp_path)

    assert kept == ["instance_config.yml"]
    assert (tmp_path / "instance_config.yml").read_text(encoding="utf-8") == "mine\n"
    assert "authentication.yml" in copied and (tmp_path / "authentication.yml").is_file()
    assert init(tmp_path)[0] == []


def test_a_process_started_with_the_directory_reads_its_declarations(tmp_path: Path):
    """The modules resolve their declarations at import: proven in a fresh process."""

    init(tmp_path)
    text = (tmp_path / "instance_config.yml").read_text(encoding="utf-8")
    (tmp_path / "instance_config.yml").write_text(text.replace("lan_hostname: GIGABYTE", "lan_hostname: ELSEWHERE"), encoding="utf-8")

    code = (
        "from aistack.web.app import INSTANCE_CONFIG;"
        "from aistack.instance.yaml.store import load_instance_config_yaml;"
        "print(load_instance_config_yaml(INSTANCE_CONFIG).lan_hostname)"
    )
    env = {**__import__("os").environ, CONFIG_DIR_ENV: str(tmp_path)}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)

    assert out.stdout.strip() == "ELSEWHERE"
    importlib.invalidate_caches()
