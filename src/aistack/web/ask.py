"""*Poser une question*: the page for everyone who uses the AI engines (`portal.chat`, ADR-0029 § 12). LAN only.

Any signed-in person asks a question in their own words; AIStack chooses the engine by `ai_policy.yml` and
says which one answered and why. The class of `portal.chat` is `internal_only` as shipped: the question stays
on the machines. What is typed is kept in memory for the length of the exchange and is never written; the
journal of calls holds the engine and the reason, never a word of it. `ask_ai` is injected so tests replace it.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.ai_runtime.question import MAX_LENGTH, OPERATION, Question
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.portal import chat, personal_data
from aistack.web.authentication import SIGNED_IN_ONLY, USER_ACTION, current_session
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/ask"
REASON_SHOWN = 200

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def _person(request: Request) -> str:
    session = current_session(request)
    return session.subject if session is not None else ""


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    language = _language(request)
    exchange = request.app.state.portal_exchanges.of(_person(request))
    answer = exchange.answer if exchange is not None else None
    notice = request.query_params.get("notice", "")

    context: dict[str, object] = {
        "base": PREFIX,
        "max_length": MAX_LENGTH,
        "where": request.app.state.portal_destination(),
        "exchange": exchange,
        "answer": answer,
        "decision": chat.decision_of(answer) if answer is not None and answer.reachable else None,
        "reason_shown": REASON_SHOWN,
        "personal": (
            ", ".join(language.t(f"ask.personal.{kind}") for kind in exchange.personal)
            if exchange is not None and exchange.personal
            else ""
        ),
        "notice": language.t(f"ask.notice.{notice}") if notice in ("empty", "too_long", "busy") else "",
        **language.context(),
    }
    response = templates.TemplateResponse(request=request, name="ask/index.html", context=context)

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response


@router.post("/ask", include_in_schema=False, dependencies=[USER_ACTION])
def ask(request: Request, question: str = Form("")) -> RedirectResponse:
    """Ask in the background and come back to the page, which refreshes until the answer is there."""

    language = _language(request)
    person = _person(request)
    text = question.strip()

    if not text:
        return RedirectResponse(f"{PREFIX}/?notice=empty", status_code=303)
    if len(text) > MAX_LENGTH:
        return RedirectResponse(f"{PREFIX}/?notice=too_long", status_code=303)

    exchange = request.app.state.portal_exchanges.start(person, text)

    if exchange is None:
        return RedirectResponse(f"{PREFIX}/?notice=busy", status_code=303)

    ask_ai = request.app.state.ask_portal
    # Before any engine is chosen: personal data found keeps the question on the machines (ADR-0029 § 5).
    exchange.personal = personal_data.screen(text).kinds

    def run() -> None:
        try:
            exchange.answer = ask_ai(Question(text), OPERATION, language.lang, personal=exchange.personal)
        except Exception:  # an engine fault must end the wait, never hang the page
            exchange.failed = True

    request.app.state.run_in_background(run)

    return RedirectResponse(f"{PREFIX}/", status_code=303)


@router.post("/new", include_in_schema=False, dependencies=[USER_ACTION])
def new(request: Request) -> RedirectResponse:
    """Forget the question and its answer, then ask another."""

    request.app.state.portal_exchanges.forget(_person(request))
    return RedirectResponse(f"{PREFIX}/", status_code=303)
