"""*Moteurs IA*: the engines asked, the policy that chooses among them, and what each call decided. LAN only.

A reading screen (`ADR-0029` § 8) over the declarations, the keys present and the journal of AI calls
(`ai-calls.jsonl`). It asks no engine, changes nothing and never shows a key or a word of a question:
the journal holds none. The policy and the engines are edited in Settings, with the other declarations.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from aistack.ai_runtime import call_journal, engines_view, reasons
from aistack.ai_runtime.policy import current_policy
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.troubleshooting import guide
from aistack.web.authentication import SIGNED_IN_ONLY
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/ai-engines"
# The counts read this many of the newest calls (the journal keeps 90 days, at most 20,000 lines).
COUNTED = 5000

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
    directory = request.app.state.generated_dir / "ai-calls"
    definition = load_ai_runtime_yaml(guide.AI_RUNTIME)
    view = engines_view.build(
        current_policy(),
        definition,
        guide.hosted_names_set(definition),
        call_journal.read(directory, COUNTED),
    )

    context: dict[str, object] = {
        "base": PREFIX,
        "view": view,
        "outside_names": dict(engines_view.HOSTED),
        "answerer": engines_view.answerer,
        "silent": lambda route: engines_view.silent_of(route),
        "reason": lambda text: reasons.localize(text, language.lang),
        **language.context(),
    }

    response = templates.TemplateResponse(request=request, name="ai_engines/index.html", context=context)

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response
