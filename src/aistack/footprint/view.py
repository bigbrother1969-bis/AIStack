"""The words a page puts on the figures: units chosen by size, a decimal comma in French, a value with its range."""

from __future__ import annotations

from collections.abc import Callable

from aistack.footprint.estimate import Triple


def number(value: float, lang: str) -> str:
    if value >= 1000:
        text = f"{value:,.0f}".replace(",", " ")
    else:
        text = f"{value:.3g}"

        if "e" in text:  # 0.000999 and the like never reach here: the unit is chosen so the value is 1 or more
            text = f"{value:.0f}"

    return text.replace(".", ",") if lang == "fr" else text


def energy(kwh: float, lang: str) -> str:
    """Final energy: kWh from one up, else Wh, else mWh, else µWh."""

    for factor, unit in ((1.0, "kWh"), (1e-3, "Wh"), (1e-6, "mWh")):
        if kwh >= factor:
            return f"{number(kwh / factor, lang)} {unit}"

    return f"{number(kwh / 1e-9, lang)} µWh" if kwh > 0 else "0 Wh"


def mass(kg: float, lang: str) -> str:
    """Greenhouse gases (GWP at 100 years): kg from one up, else g, else mg, else µg."""

    for factor, unit in ((1.0, "kgCO2e"), (1e-3, "gCO2e"), (1e-6, "mgCO2e")):
        if kg >= factor:
            return f"{number(kg / factor, lang)} {unit}"

    return f"{number(kg / 1e-9, lang)} µgCO2e" if kg > 0 else "0 gCO2e"


def span(triple: Triple, show: Callable[[float, str], str], lang: str) -> tuple[str, str]:
    """The central value, and the range it sits in."""

    return show(triple.central, lang), f"{show(triple.low, lang)} – {show(triple.high, lang)}"
