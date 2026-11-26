from __future__ import annotations

from pathlib import Path

import pytest

from aistack.boot_checks.definition import DEFAULT_SEVERITY, FINDINGS, SEVERITIES
from aistack.boot_checks.load import load_boot_checks_yaml
from aistack.declaration.validate import LOADERS

SHIPPED = (
    Path(__file__).resolve().parents[3]
    / "src/aistack/boot_checks/definitions/boot_checks.yml"
)


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "b.yml"
    path.write_text(text, encoding="utf-8")

    return path


def test_the_shipped_declaration_loads_with_neutral_values():
    definition = load_boot_checks_yaml(SHIPPED)

    assert definition.settle_minutes == 10
    assert (
        definition.expected_containers == ()
        and definition.expected_stopped == ()
        and definition.mounts == ()
    )
    assert definition.docker_user_rules is None
    assert definition.severity == DEFAULT_SEVERITY
    assert definition.companions and not definition.indicator_weighted
    assert (definition.ai_enabled, definition.ai_max_extra_controls) == (True, 3)
    assert (definition.summary_enabled, definition.summary_at) == (True, "08:00")


def test_every_finding_has_a_default_weight_and_only_known_levels():
    assert set(DEFAULT_SEVERITY) == set(FINDINGS)
    assert set(DEFAULT_SEVERITY.values()) <= set(SEVERITIES)


def test_the_declaration_is_registered_with_the_validator():
    assert "boot_checks.yml" in LOADERS


def test_an_empty_file_is_the_defaults(tmp_path: Path):
    assert load_boot_checks_yaml(_write(tmp_path, "")).settle_minutes == 10


def test_the_owner_s_declaration_is_read(tmp_path: Path):
    path = _write(
        tmp_path,
        "expected_containers: [a, b]\nexpected_stopped: [c]\nmounts: [/srv]\ndocker_user_rules: 7\n"
        'severity:\n  kvm_modules: warning\ncompanions: false\nsummary:\n  at: "07:30"\n  enabled: false\n'
        "ai:\n  max_extra_controls: 1\n",
    )

    definition = load_boot_checks_yaml(path)

    assert definition.expected_containers == (
        "a",
        "b",
    ) and definition.expected_stopped == ("c",)
    assert definition.mounts == ("/srv",) and definition.docker_user_rules == 7
    assert (
        definition.severity["kvm_modules"] == "warning"
        and definition.severity["failed_unit"] == "critical"
    )
    assert not definition.companions and not definition.summary_enabled
    assert (definition.summary_at, definition.ai_max_extra_controls) == ("07:30", 1)


@pytest.mark.parametrize(
    "text",
    [
        "settle_minutes: 0\n",
        "expected_containers: a\n",
        "mounts: [srv]\n",
        "docker_user_rules: -1\n",
        "severity:\n  nothing: warning\n",
        "severity:\n  kvm_modules: loud\n",
        "severity: [a]\n",
        "companions: yes please\n",
        "companion_silent_minutes: 0\n",
        "companion_mounts: [a]\n",
        "companion_mounts:\n  pi: [media]\n",
        'summary:\n  at: "8h"\n',
        "ai: on\n",
        "- a\n",
    ],
)
def test_a_wrong_declaration_says_so(tmp_path: Path, text: str):
    with pytest.raises(ValueError):
        load_boot_checks_yaml(_write(tmp_path, text))


def test_the_probes_and_the_ups_statuses_are_read(tmp_path: Path):
    definition = load_boot_checks_yaml(_write(tmp_path, "probes:\n  proxy: 200\n  web: 301\nups_expected: [OL, CHRG]\n"))

    assert definition.probes == {"proxy": 200, "web": 301}
    assert definition.ups_expected == ("OL", "CHRG")


@pytest.mark.parametrize("text", ["probes: [a]\n", "probes:\n  x: ok\n", "probes:\n  x: 42\n", "ups_expected: []\n", "ups_expected: OL\n"])
def test_a_wrong_probe_or_ups_declaration_says_so(tmp_path: Path, text: str):
    with pytest.raises(ValueError):
        load_boot_checks_yaml(_write(tmp_path, text))


def test_the_companions_are_declared_by_host_name(tmp_path: Path):
    definition = load_boot_checks_yaml(_write(tmp_path, "companion_silent_minutes: 30\ncompanion_mounts:\n  backup-host: [/media/BACKUP]\n"))
    shipped = load_boot_checks_yaml(SHIPPED)

    assert definition.companion_silent_minutes == 30 and definition.companion_mounts == {"backup-host": ("/media/BACKUP",)}
    assert shipped.companion_silent_minutes == 45 and shipped.companion_mounts == {}
