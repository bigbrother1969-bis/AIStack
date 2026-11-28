"""La console simplifiée pour l'utilisateur non-admin (ADR-0033).

CN0 n'était qu'un squelette. Ce lot (CN1) y met la maquette (variante
C, du canvas Design) avec des valeurs figées — aucune source réelle
branchée (CN2), aucun lien « Mode avancé » gardé par le profil (CN3).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from aistack.web.authentication import SIGNED_IN_ONLY
from aistack.web.exposure import PUBLIC
from aistack.web.templating import templates

PREFIX = "/simple"

# Like Architecture and the Health cockpit (ADR-0014 § 5), not like the
# bare console: this screen shows the same infrastructure status
# (security, backups, disk, updates), so it needs a session too.
router = APIRouter(dependencies=[PUBLIC, SIGNED_IN_ONLY])

_RADIUS = 54
_CIRCUMFERENCE = 2 * math.pi * _RADIUS
_GREEN = "#2E7D32"
_AMBER = "#F59E0B"
_GREY = "#6B7280"
_AMBER_TEXT = "#B45309"


@dataclass(frozen=True)
class _Gauge:
    label: str
    value: int
    status_text: str
    has_issue: bool = False


# Fixed demo values (CN1): the real sources are CN2's job.
_GAUGES = (
    _Gauge("Sécurité", 100, "Protégée"),
    _Gauge("Sauvegardes", 60, "À surveiller", has_issue=True),
    _Gauge("Espace disque", 72, "Suffisant"),
    _Gauge("Mises à jour", 100, "À jour"),
)


def _ring(value: int) -> str:
    filled = (value / 100) * _CIRCUMFERENCE
    remaining = _CIRCUMFERENCE - filled
    return f"{filled:.2f} {remaining:.2f}"


def _item(gauge: _Gauge) -> dict[str, Any]:
    perfect = gauge.value == 100
    return {
        "label": gauge.label,
        "dasharray": _ring(gauge.value),
        "ring_color": _AMBER if gauge.has_issue else _GREEN,
        "center_text": "✓" if perfect else f"{gauge.value}%",
        "text_y": 88 if perfect else 90,
        "text_size": 30 if perfect else 26,
        "status_color": _AMBER_TEXT if gauge.has_issue else _GREY,
        "status_text": gauge.status_text,
        "show_button": gauge.has_issue,
    }


def _index(request: Request) -> HTMLResponse:
    items = [_item(gauge) for gauge in _GAUGES]
    headline = (
        "Un point mérite votre attention — l'IA peut s'en charger."
        if any(gauge.has_issue for gauge in _GAUGES)
        else "Tout est vert : rien à faire aujourd'hui."
    )
    return templates.TemplateResponse(
        request=request,
        name="simple_console/index.html",
        context={"items": items, "headline": headline},
    )


# Both forms declared explicitly: `app.router.redirect_slashes` is off
# (`aistack.web.app.create_app`), so a screen must answer both itself.
router.add_api_route("", _index, methods=["GET", "HEAD"], include_in_schema=False)
router.add_api_route("/", _index, methods=["GET", "HEAD"], include_in_schema=False)
