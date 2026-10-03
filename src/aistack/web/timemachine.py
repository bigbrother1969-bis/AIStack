"""
*Time Machine* — the graph of what AIStack observed, browsed by stream,
by network tree and on a time ribbon (`ADR-0011`; the screen
`timemachine_ui` served on port 8186 until 2026-10-03, `ADR-0012`).
LAN only: it shows the commands, packages and AI reasoning the host
recorded.

A thin adapter over `aistack.timemachine.screen`. The graph is rebuilt
by `aistack.cli.timemachine_rebuild`, never from here; the only writes
are an administrator's acts on an Explication (`ADR-0015`), recorded in
the Explications store and seen by the graph at the next rebuild. One
collaborator reaches the routes through the application, so a test
replaces it: `network_tree` (the live Docker and Compose discovery,
cached for 45 s). The graph, the Explications and the last network scan
are read under the application's generated directory, the graph opened
read-only afresh on each request, so a rebuild is seen without a
restart.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from aistack.authentication.sessions import LOCAL
from aistack.explications import human
from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.renderers.assets import MARK_DATA_URI
from aistack.renderers.nav import PAGE_NAV_STYLE, render_page_nav
from aistack.renderers.timemachine import render_provenance_mermaid
from aistack.timemachine.iri import short_label
from aistack.timemachine.screen import (
    EXPLICATIONS_DIR,
    GRAPH_DIR,
    RibbonEntries,
    explication_panel,
    mermaid_script,
    node_instant,
    node_ribbon_panel,
    node_stable_subject,
    node_view,
    open_graph,
    provenance_neighbors,
    reconstitution,
    ribbon_page,
    stream_list,
    tree_context,
)
from aistack.web.authentication import ADMIN, ADMIN_ACTION, SIGNED_IN_ONLY, current_profile, current_session
from aistack.web.exposure import LAN_ONLY
from aistack.web.templating import templates

PREFIX = "/timemachine"

router = APIRouter(dependencies=[LAN_ONLY, SIGNED_IN_ONLY])


def _language(request: Request) -> PageLanguage:
    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
        request.app.state.languages,
    )


def _node_href(language: PageLanguage) -> Any:
    return lambda iri: f"{PREFIX}/node?iri={quote(iri, safe='')}&lang={language.lang}"


def _render(
    request: Request,
    language: PageLanguage,
    name: str,
    context: dict[str, Any],
    extra_query: str = "",
) -> Response:
    response = templates.TemplateResponse(
        request=request,
        name=f"timemachine/{name}",
        context={
            **context,
            "base": PREFIX,
            "favicon": MARK_DATA_URI,
            "page_nav_style": PAGE_NAV_STYLE,
            # Relative links: the console and Settings are served by
            # this same application, on this same port.
            "page_nav": render_page_nav(
                language.t,
                request.app.state.languages,
                language.lang,
                extra_query=extra_query,
            ),
            **language.context(),
        },
    )

    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)

    return response


def _not_built(request: Request, language: PageLanguage) -> Response:
    store_path = request.app.state.generated_dir / GRAPH_DIR
    return _render(request, language, "not_built.html", {"store_path": str(store_path)})


def _ribbon_entries(request: Request, store: Any) -> list[dict[str, Any]]:
    cache: RibbonEntries | None = getattr(request.app.state, "timemachine_ribbon", None)
    if cache is None:
        cache = RibbonEntries(request.app.state.generated_dir)
        request.app.state.timemachine_ribbon = cache
    return cache.get(store)


def _tree(request: Request, store: Any, query: str) -> dict[str, Any]:
    return tree_context(request.app.state.network_tree(), store, query)


def _query(**parts: str) -> str:
    return "".join(f"&{name}={quote(value)}" for name, value in parts.items() if value)


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def streams(request: Request) -> Response:
    language = _language(request)
    store = open_graph(request.app.state.generated_dir)
    if store is None:
        return _not_built(request, language)

    return _render(request, language, "streams.html", {"streams": stream_list(store)})


@router.get("/node", response_class=HTMLResponse, include_in_schema=False)
def node(request: Request, iri: str, q: str = "") -> Response:
    """One node: its facts, what points at it, its provenance diagram,
    with the network tree on its left and its own chronology beside it."""

    language = _language(request)
    store = open_graph(request.app.state.generated_dir)
    if store is None:
        return _not_built(request, language)

    try:
        view = node_view(store, iri)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    href = _node_href(language)
    neighbors = provenance_neighbors(view, language.t, href)
    provenance_graph = render_provenance_mermaid(short_label(iri), neighbors) if neighbors else None
    tree = _tree(request, store, q)
    subject = node_stable_subject(view.facts)

    return _render(
        request,
        language,
        "node.html",
        {
            "iri": iri,
            "node_type_label_key": view.type_label_key,
            "instants": view.instants,
            "facts": view.facts,
            "referenced_by": view.referenced_by,
            "provenance_graph": provenance_graph,
            # A multi-megabyte bundle: only embedded when there is a diagram.
            "mermaid_js": mermaid_script() if provenance_graph else None,
            "tree_root": tree["root"],
            "tree_query": tree["query"],
            "tree_search_empty": tree["search_empty"],
            "ribbon_panel": node_ribbon_panel(_ribbon_entries(request, store), subject, href),
            "node_instant": node_instant(view.facts),
        },
        extra_query=_query(iri=iri, q=q),
    )


@router.get("/tree", response_class=HTMLResponse, include_in_schema=False)
def tree(request: Request, q: str = "") -> Response:
    """The network tree, from the live catalogs; each node's history
    looked up in the graph (none when it has never been built)."""

    language = _language(request)
    store = open_graph(request.app.state.generated_dir)

    return _render(request, language, "tree.html", _tree(request, store, q), extra_query=_query(q=q))


@router.get("/ribbon", response_class=HTMLResponse, include_in_schema=False)
def ribbon(
    request: Request,
    streams: list[str] = Query(default=[]),
    submitted: str = "",
    subject: str = "",
    page: int = Query(default=1, ge=1),
) -> Response:
    """Every recorded instant on a time axis, filterable by stream and by
    subject. The hidden `submitted` field tells a form submitted with
    every stream unchecked (show nothing) from a bare link (show all)."""

    language = _language(request)
    store = open_graph(request.app.state.generated_dir)
    if store is None:
        return _not_built(request, language)

    subject = subject.strip()
    context = ribbon_page(
        _ribbon_entries(request, store),
        streams=streams,
        submitted=bool(submitted),
        subject=subject,
        page=page,
        node_href=_node_href(language),
    )
    filter_query = "".join(f"&streams={quote(stream)}" for stream in streams)
    if submitted:
        filter_query += "&submitted=1"
    filter_query += _query(subject=subject)
    context["filter_query"] = filter_query

    extra_query = filter_query
    if context["page"] != 1:
        extra_query += f"&page={context['page']}"

    return _render(request, language, "ribbon.html", context, extra_query=extra_query)


@router.get("/reconstitute", response_class=HTMLResponse, include_in_schema=False)
def reconstitute(request: Request, subject: str = "", as_of: str = "") -> Response:
    """What was known about one subject at one instant — reached from a
    node, which supplies both; without either, nothing is guessed."""

    language = _language(request)
    store = open_graph(request.app.state.generated_dir)
    if store is None:
        return _not_built(request, language)

    subject, as_of = subject.strip(), as_of.strip()
    panel = (
        reconstitution(store, _ribbon_entries(request, store), subject, as_of, _node_href(language))
        if subject and as_of
        else None
    )

    return _render(
        request,
        language,
        "reconstitute.html",
        {"subject": subject, "as_of": as_of, "panel": panel},
        extra_query=_query(subject=subject, as_of=as_of),
    )


@router.get("/explication", response_class=HTMLResponse, include_in_schema=False)
def explication(request: Request, subject: str = "", done: str = "", refused: str = "") -> Response:
    """Every recorded version of one subject's Explication; for an
    administrator, the forms to write, validate or discard (`ADR-0015`)."""

    language = _language(request)
    store = open_graph(request.app.state.generated_dir)
    if store is None:
        return _not_built(request, language)

    subject = subject.strip()
    panel = explication_panel(subject, request.app.state.generated_dir) if subject else None

    return _render(
        request,
        language,
        "explication.html",
        {
            "subject": subject,
            "panel": panel,
            "is_admin": current_profile(request) == ADMIN,
            "done": _DONE.get(done, ""),
            "refused": refused if refused.startswith("timemachine.explication.refused.") else "",
        },
        extra_query=_query(subject=subject),
    )


# --------------------------------------------------------------------
# Writing, validating, discarding (ADR-0015) — administrators only
# --------------------------------------------------------------------

_DONE = {
    "written": "timemachine.explication.done.written",
    "validated": "timemachine.explication.done.validated",
    "discarded": "timemachine.explication.done.discarded",
}


def _person(request: Request) -> human.Person:
    session = current_session(request)
    assert session is not None  # ADMIN_ACTION ran first
    name = "local-admin" if session.method == LOCAL else session.name
    return human.Person(source=human.person_source(session.subject), name=name)


def _back(subject: str, **outcome: str) -> RedirectResponse:
    return RedirectResponse(f"{PREFIX}/explication?subject={quote(subject)}{_query(**outcome)}", status_code=303)


def _act(request: Request, subject: str, done: str, act: Any) -> Response:
    try:
        act(request.app.state.generated_dir / EXPLICATIONS_DIR)
    except human.ExplicationChanged as error:
        language = _language(request)
        response = _render(
            request,
            language,
            "explication.html",
            {
                "subject": subject,
                "panel": explication_panel(subject.strip(), request.app.state.generated_dir) if subject.strip() else None,
                "is_admin": True,
                "done": "",
                "refused": error.reason,
            },
            extra_query=_query(subject=subject),
        )
        response.status_code = 409
        return response
    except human.ExplicationRefused as error:
        return _back(subject, refused=error.reason)
    return _back(subject, done=done)


@router.post("/explication/write", include_in_schema=False, dependencies=[ADMIN_ACTION])
def explication_write(
    request: Request,
    subject: str = Form(""),
    text: str = Form(""),
    expected: int = Form(-1),
) -> Response:
    person = _person(request)
    return _act(request, subject, "written", lambda out: human.write(subject, text, person, out, expected))


@router.post("/explication/validate", include_in_schema=False, dependencies=[ADMIN_ACTION])
def explication_validate(request: Request, subject: str = Form(""), expected: int = Form(-1)) -> Response:
    person = _person(request)
    return _act(request, subject, "validated", lambda out: human.validate(subject, person, out, expected))


@router.post("/explication/discard", include_in_schema=False, dependencies=[ADMIN_ACTION])
def explication_discard(
    request: Request,
    subject: str = Form(""),
    reason: str = Form(""),
    expected: int = Form(-1),
) -> Response:
    person = _person(request)
    return _act(request, subject, "discarded", lambda out: human.discard(subject, reason, person, out, expected))
