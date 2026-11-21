"""`footprint.yml`: the shipped file loads, and a file that hides where a figure comes from is refused."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aistack.footprint.declaration import DEFINITION, REQUIRED, load_footprint_yaml


def edited(tmp_path: Path, change) -> Path:
    data = yaml.safe_load(DEFINITION.read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / "footprint.yml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_the_shipped_declaration_loads_with_every_parameter():
    declaration = load_footprint_yaml(DEFINITION)

    assert [p.name for p in declaration.parameters] == list(REQUIRED)
    assert declaration.period_days == 30
    assert "portal.chat" in declaration.terminal_callers


def test_every_shipped_figure_says_where_it_comes_from():
    for parameter in load_footprint_yaml(DEFINITION).parameters:
        assert parameter.source and parameter.status in ("measured", "sourced", "declared")


def test_the_gpu_idle_power_is_the_one_measured_on_the_machine():
    idle = load_footprint_yaml(DEFINITION).get("gpu_idle_watts")

    assert (idle.central, idle.status) == (33.57, "measured")


def test_the_scenarios_of_a_parameter_are_read_by_name():
    grid = load_footprint_yaml(DEFINITION).get("grid_local")

    assert (grid.at("low"), grid.at("central"), grid.at("high")) == (grid.low, grid.central, grid.high)


@pytest.mark.parametrize(
    ("change", "words"),
    [
        (lambda d: d["parameters"].pop("grid_local"), "grid_local"),
        (lambda d: d["parameters"]["grid_local"].pop("high"), "grid_local.high"),
        (lambda d: d["parameters"]["grid_local"].update(source="  "), "source"),
        (lambda d: d["parameters"]["grid_local"].update(status="guessed"), "status"),
        (lambda d: d["parameters"]["grid_local"].update(low=-1), "grid_local.low"),
        (lambda d: d["parameters"]["host_lifetime_years"].update(low=0), "host_lifetime_years"),
        (lambda d: d.update(period_days=0), "period_days"),
        (lambda d: d["method"].pop("reference"), "method.reference"),
        (lambda d: d.update(terminal_callers="portal.chat"), "terminal_callers"),
    ],
)
def test_a_file_that_hides_a_figure_or_its_source_is_refused(tmp_path, change, words):
    with pytest.raises(ValueError, match=words):
        load_footprint_yaml(edited(tmp_path, change))


def test_a_file_that_is_not_a_mapping_is_refused(tmp_path):
    path = tmp_path / "footprint.yml"
    path.write_text("- just\n- a list\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mapping"):
        load_footprint_yaml(path)


def test_the_method_names_its_reference_without_claiming_conformity():
    method = load_footprint_yaml(DEFINITION).method

    assert "SPEC 2314" in method.reference
    assert "conform" not in method.functional_unit.lower()
