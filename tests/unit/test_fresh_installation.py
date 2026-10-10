"""
A new installation carries nothing of the reference host (2.0.0-rc1, the
owner 2026-10-10: "vérifier que la procédure d'installation installe une
version propre et qui ne ramène aucune info de ma configuration
actuelle : tout doit être découvert par AIStack").

The package ships neutral declarations; GIGABYTE's own live in
tests/reference/definitions, which the suite reads (tests/conftest.py).
These tests read the package as a new installation does — without the
reference directory — and look for the reference host's names in what
it ships and in every page it serves.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


from aistack.cli.config_init import GENERATION, GENERATION_FILE, init
from aistack.config import PACKAGE_ROOT, shipped_definitions
from aistack.instance.declarations import SEEN_RECORD
from aistack.instance.first_start import SHIPPED_RECORD, fingerprint, still_shipped

ROOT = Path(__file__).resolve().parents[2]

# What names the reference host, its people, its places and its devices.
REFERENCE = re.compile(
    r"GIGABYTE|gigabyte|persiaut|Persiaut|PERSIAUT|TechData|[Rr]aspberry|big-brother|"
    r"192\.168\.1\.(10|99|254)|sarfatti|PNTJYZD|/media/(Films|Multimedia|Comics|BD|Documents|TechData)\b|"
    r"Freebox|pi-hole\.persiaut"
)


def found_in(text: str) -> list[str]:
    return sorted({match.group(0) for match in REFERENCE.finditer(text)})


def test_every_shipped_declaration_is_neutral():
    shipped = shipped_definitions()

    assert len(shipped) >= 20
    for path in shipped:
        assert found_in(path.read_text(encoding="utf-8")) == [], path.name


def test_the_pages_texts_name_no_reference_host():
    """The catalogs, the manual and every template, but their Jinja comments."""

    sources = [
        *sorted((PACKAGE_ROOT / "i18n" / "catalogs").rglob("*.yml")),
        *sorted((PACKAGE_ROOT / "manual").glob("manual.*.md")),
        *sorted((PACKAGE_ROOT / "web" / "templates").rglob("*.html")),
    ]
    for path in sources:
        text = re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.S)
        assert found_in(text) == [], path.relative_to(PACKAGE_ROOT)


def test_the_reference_declarations_are_the_reference_host_s():
    """The other half: the suite still reads GIGABYTE's own."""

    reference = ROOT / "tests" / "reference" / "definitions"
    names = {path.name for path in reference.glob("*.yml")}

    assert {path.name for path in shipped_definitions()} <= names
    assert "lan_hostname: GIGABYTE" in (reference / "instance_config.yml").read_text(encoding="utf-8")


def test_a_new_directory_receives_neutral_copies(tmp_path: Path):
    copied, kept, updated = init(tmp_path)

    assert kept == [] and updated == []
    assert len(copied) == len(shipped_definitions())
    for name in copied:
        assert found_in((tmp_path / name).read_text(encoding="utf-8")) == [], name
    assert (tmp_path / GENERATION_FILE).read_text(encoding="utf-8").strip() == GENERATION
    # Still the shipped values: the first start list asks for them.
    assert still_shipped(tmp_path, "instance_config.yml")


def test_a_directory_filled_before_keeps_the_reference_host_s_values(tmp_path: Path):
    """GIGABYTE's ./config: copies of the reference host's values its owner
    lives on, recorded as untouched — they must never follow the neutral
    declarations."""

    reference = ROOT / "tests" / "reference" / "definitions"
    for name in ("instance_config.yml", "sync.yml", "pra_tests.yml"):
        (tmp_path / name).write_bytes((reference / name).read_bytes())
    record = {name: fingerprint(tmp_path / name) for name in ("instance_config.yml", "sync.yml", "pra_tests.yml")}
    (tmp_path / SHIPPED_RECORD).write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / SEEN_RECORD).write_text(json.dumps(record), encoding="utf-8")

    _copied, _kept, updated = init(tmp_path)

    assert updated == []
    for name in record:
        assert (tmp_path / name).read_bytes() == (reference / name).read_bytes(), name
        assert not still_shipped(tmp_path, name)
    # Adopted once: a later start changes nothing either.
    assert init(tmp_path)[2] == []


def test_auto_finds_the_lan_of_the_default_route():
    from aistack.network_discovery.definition import discover_cidr

    routes = (
        "Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\tWindow\tIRTT\n"
        "enp2s0\t00000000\tFE01A8C0\t0003\t0\t0\t100\t00000000\t0\t0\t0\n"
        "docker0\t000011AC\t00000000\t0001\t0\t0\t0\t0000FFFF\t0\t0\t0\n"
        "enp2s0\t0001A8C0\t00000000\t0001\t0\t0\t100\t00FFFFFF\t0\t0\t0\n"
    )

    assert discover_cidr(routes) == "192.168.1.0/24"
    assert discover_cidr("Iface\tDestination\n") is None


def test_a_new_installation_serves_every_page_and_names_no_reference_host(tmp_path: Path):
    config = tmp_path / "config"
    generated = tmp_path / "work" / "reports" / "generated"
    generated.mkdir(parents=True)
    init(config)
    env = {key: value for key, value in os.environ.items() if key != "AISTACK_REFERENCE_DIR"}
    env |= {"AISTACK_CONFIG_DIR": str(config), "PYTHONPATH": f"{ROOT / 'src'}{os.pathsep}{ROOT}"}

    result = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "unit" / "fresh_installation_probe.py"), str(generated)],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stderr[-3000:]
    lines = result.stdout.splitlines()
    assert [line for line in lines if line.startswith("RENDERED")] == [
        "RENDERED console.html []",
        "RENDERED health.html []",
    ]
    assert [line for line in lines if line.startswith("REFERENCE")] == []
    statuses = [line.split(" ", 1) for line in lines if line[:3].isdigit()]
    assert len([status for status, _path in statuses if status == "200"]) >= 25
    assert [path for status, path in statuses if status == "500"] == []
