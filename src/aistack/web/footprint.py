"""
*Usage et empreinte*: what AIStack's AI calls amount to and what they cost in energy and greenhouse gases
(`ADR-0030`). LAN only, a reading screen over the journal of AI calls and `footprint.yml`: it asks no engine,
changes nothing and shows no word of any question, because the journal holds none.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from aistack.ai_runtime import call_journal
from aistack.footprint import estimate, view
from aistack.footprint.declaration import load_footprint_yaml
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.web.authentication import SIGNED_IN_ONLY
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/footprint"
# The calculation reads this many of the newest calls (the journal keeps 90 days, at most 20,000 lines).
COUNTED = 20000

# What the page says it does not count, one catalog key each.
LIMITS = ("indicators", "unanswered", "host_making", "training", "water", "places", "conformity")

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    language = _language(request)
    lang = language.lang
    error = ""
    declaration = None
    result = None

    try:
        declaration = load_footprint_yaml()
    except ValueError as problem:
        error = str(problem)

    if declaration is not None:
        directory = request.app.state.generated_dir / "ai-calls"
        result = estimate.estimate(call_journal.read(directory, COUNTED), declaration)

    context: dict[str, object] = {
        "base": PREFIX,
        "error": error,
        "declaration": declaration,
        "result": result,
        "levels": estimate.LEVELS,
        "limits": LIMITS,
        "energy": lambda triple: view.span(triple, view.energy, lang),
        "mass": lambda triple: view.span(triple, view.mass, lang),
        "one_energy": lambda kwh: view.energy(kwh, lang),
        "one_mass": lambda kg: view.mass(kg, lang),
        "plain": lambda value: view.number(value, lang),
        **language.context(),
    }

    response = templates.TemplateResponse(request=request, name="footprint/index.html", context=context)

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response
