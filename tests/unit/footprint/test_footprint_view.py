"""The units and the decimal sign a page puts on the figures."""

from __future__ import annotations

import pytest

from aistack.footprint.estimate import Triple
from aistack.footprint.view import energy, mass, number, span


@pytest.mark.parametrize(
    ("kwh", "text"),
    [(3.6, "3,6 kWh"), (0.0004, "400 mWh"), (0.0425, "42,5 Wh"), (1500.0, "1 500 kWh"), (0.0, "0 Wh")],
)
def test_energy_takes_its_unit_from_its_size(kwh, text):
    assert energy(kwh, "fr") == text


@pytest.mark.parametrize(
    ("kg", "text"),
    [(0.149, "149 gCO2e"), (2.5, "2,5 kgCO2e"), (0.0000345, "34,5 mgCO2e"), (0.0, "0 gCO2e")],
)
def test_greenhouse_gases_take_their_unit_from_their_size(kg, text):
    assert mass(kg, "fr") == text


def test_english_keeps_the_decimal_point():
    assert number(3.6, "en") == "3.6" and number(3.6, "fr") == "3,6"
    assert energy(0.0425, "en") == "42.5 Wh"


def test_a_span_gives_the_central_value_and_the_range():
    assert span(Triple(0.001, 0.002, 0.004), energy, "en") == ("2 Wh", "1 Wh – 4 Wh")
