"""La console simplifiée pour l'utilisateur non-admin (ADR-0033).

CN0 n'était qu'un squelette ; CN1 y a mis la maquette (variante C) avec
des valeurs figées. Ce lot (CN2) branche les quatre jauges sur des
signaux réels déjà calculés ailleurs dans AIStack — cet écran n'invente
aucun nouveau calcul de santé, il les restitue sous une forme
simplifiée, à chaque chargement de page :

- Sécurité : les constats du Cybersecurity Manager
  (`aistack.web.pending.security_attention`, ADR-0028).
- Sauvegardes : l'indicateur des contrôles du matin
  (`aistack.boot_checks.screen.read_indicator`, ADR-0032).
- Espace disque : les constats de stockage du cockpit santé
  (`aistack.tasks.boot_check.cockpit_readings`, premier élément —
  OPS-0005 ; décidé le 2026-11-28 par AskUserQuestion après lecture du
  dépôt, le découpage disait à tort « Inventaire Docker / hôtes »,
  module qui n'existe pas tel quel).
- Mises à jour : l'état des propositions déjà gouvernées par le quai
  (`aistack.dock.proposals.all_proposals`, ADR-0019) — décidé le
  2026-11-28 par AskUserQuestion : pas de vérification live
  (`aistack.dock.candidates.inspect_all`), qui appellerait le registre
  d'images par le réseau à chaque chargement de cet écran non-admin ;
  le découpage disait à tort « Cockpit santé », qui ne porte aucun
  domaine « mises à jour ».

CN3 (mode avancé gardé par le profil) reste à faire.
"""

from __future__ import annotations

import math
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from aistack.boot_checks.screen import LEVELS as BOOT_CHECK_LEVELS, read_indicator
from aistack.dock.proposals import FAILED, PROPOSED, RUNNING, VALIDATED, all_proposals
from aistack.security.findings import FIX, URGENT
from aistack.tasks.boot_check import cockpit_readings
from aistack.web.authentication import SIGNED_IN_ONLY
from aistack.web.exposure import PUBLIC
from aistack.web.pending import security_attention
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

# A proposal not yet settled, read from `aistack.dock.proposals`: still on the dock.
_PENDING_PROPOSAL = (PROPOSED, VALIDATED, RUNNING)


@dataclass(frozen=True)
class _Gauge:
    label: str
    value: int
    status_text: str
    has_issue: bool = False
    # Nothing was measured (no provider, no declaration): neither green nor
    # amber would be honest, so this draws its own, neutral, grey state.
    not_measured: bool = False


def _security_gauge(generated_dir: Path) -> _Gauge:
    found = security_attention(generated_dir)
    if found.level is None:
        return _Gauge("Sécurité", 100, "Protégée")
    text = f"{found.count} constat(s) à traiter"
    if found.level == URGENT:
        return _Gauge("Sécurité", 15, text, has_issue=True)
    if found.level == FIX:
        return _Gauge("Sécurité", 45, text, has_issue=True)
    return _Gauge("Sécurité", 70, text, has_issue=True)  # watch


def _backup_gauge(generated_dir: Path) -> _Gauge:
    shown = read_indicator(generated_dir)
    level = BOOT_CHECK_LEVELS.get(shown.status, "not-instrumented")
    if level == "not-instrumented":
        return _Gauge("Sauvegardes", 0, "Non mesuré", not_measured=True)
    if level == "clean":
        return _Gauge("Sauvegardes", 100, "À jour")
    if level == "alert":
        return _Gauge("Sauvegardes", 20, f"{shown.anomalies} anomalie(s) à corriger", has_issue=True)
    return _Gauge("Sauvegardes", 55, f"{shown.anomalies} anomalie(s) à surveiller", has_issue=True)  # watch


def _storage_gauge(hostname: str) -> _Gauge:
    storage = cockpit_readings(hostname)[0]  # (stockage, sauvegardes) : seul le premier concerne ce lot
    if not storage.instrumented:
        return _Gauge("Espace disque", 0, "Non mesuré", not_measured=True)
    if storage.findings == 0:
        return _Gauge("Espace disque", 100, "Suffisant")
    return _Gauge("Espace disque", 50, f"{storage.findings} volume(s) à surveiller", has_issue=True)


def _updates_gauge(generated_dir: Path) -> _Gauge:
    latest_by_service: dict[str, str] = {}
    for proposal in all_proposals(generated_dir):  # déjà du plus récent au plus ancien
        latest_by_service.setdefault(proposal.service, proposal.status)

    statuses = latest_by_service.values()
    if any(status == FAILED for status in statuses):
        return _Gauge("Mises à jour", 30, "Une mise à jour a échoué", has_issue=True)
    if any(status in _PENDING_PROPOSAL for status in statuses):
        return _Gauge("Mises à jour", 60, "Une mise à jour attend une décision", has_issue=True)
    return _Gauge("Mises à jour", 100, "À jour")


def _gauges(request: Request) -> tuple[_Gauge, ...]:
    generated_dir: Path = request.app.state.generated_dir
    hostname = socket.gethostname()
    return (
        _security_gauge(generated_dir),
        _backup_gauge(generated_dir),
        _storage_gauge(hostname),
        _updates_gauge(generated_dir),
    )


def _ring(value: int) -> str:
    filled = (value / 100) * _CIRCUMFERENCE
    remaining = _CIRCUMFERENCE - filled
    return f"{filled:.2f} {remaining:.2f}"


def _item(gauge: _Gauge) -> dict[str, Any]:
    perfect = gauge.value == 100 and not gauge.not_measured
    ring_color = _GREY if gauge.not_measured else (_AMBER if gauge.has_issue else _GREEN)
    return {
        "label": gauge.label,
        "dasharray": _ring(gauge.value),
        "ring_color": ring_color,
        "center_text": "?" if gauge.not_measured else ("✓" if perfect else f"{gauge.value}%"),
        "text_y": 88 if perfect or gauge.not_measured else 90,
        "text_size": 30 if perfect or gauge.not_measured else 26,
        "status_color": _AMBER_TEXT if gauge.has_issue else _GREY,
        "status_text": gauge.status_text,
        "show_button": gauge.has_issue,
    }


def _index(request: Request) -> HTMLResponse:
    gauges = _gauges(request)
    items = [_item(gauge) for gauge in gauges]
    headline = (
        "Un point mérite votre attention — l'IA peut s'en charger."
        if any(gauge.has_issue for gauge in gauges)
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
