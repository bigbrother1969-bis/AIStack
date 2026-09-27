from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from aistack.i18n import LANGUAGE_COOKIE, LANGUAGE_PARAMETER
from aistack.i18n.web import PageLanguage, page_language
from aistack.providers.repository import RepositoryProvider
from aistack.timemachine import OxigraphGraphStore, stream_stem
from aistack.timemachine.projection import DEFAULT_GENERATED_DIR
from aistack.timemachine.vocabulary import (
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_USED,
    PROV_WAS_ATTRIBUTED_TO,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
)

# A fifth mini-app, same family as `priority_ui`/`selection_ui`/
# `network_discovery_ui`/`troubleshooting_assistant_ui` — decided with
# the owner 2026-09-27 over a static-HTML page generated once by a CLI
# command (`console_render`'s own pattern): the Time Machine is
# something a person chooses an instant or a subject in and follows
# provenance edges from, not a fixed snapshot.
#
# **LAN-only, the same way as the other four (`ADR-0011` roadmap R1) —
# an operational convention, not a code-level restriction.** Bound to
# `0.0.0.0` below so it is reachable from anywhere on the owner's own
# LAN (`run_timemachine_ui.sh`'s own comment gives the exact reasoning
# `run_network_discovery_ui.sh` already established); LAN-only comes
# from never declaring a Proxy Host for this port in Nginx Proxy
# Manager, and from `console_links.yml` linking to the direct LAN
# address, never a `...persiaut-family.fr` subdomain. R1 stays true
# until 1.7's connection layer exists — this screen shows the same
# commands, packages and AI reasoning `network_discovery_ui`'s own
# warning already calls "a reconnaissance map for an attacker".
#
# **Read-only, never a writer** (`ADR-0011` § *Decision* 10:
# reconstruction is a full rebuild, on demand, run by
# `aistack.cli.timemachine_rebuild` — never by a screen a browser
# reaches). `OxigraphGraphStore.read_only` opens a fresh handle per
# request rather than holding one for the process's lifetime — cheap
# (SPARQL over an on-disk RocksDB store, not a network round trip),
# and it means a rebuild that replaces the store between two requests
# is picked up by the next one without a restart, with no long-lived
# handle to keep coordinated with the owner's own rebuild command.
#
# **v1 scope, chosen with the owner 2026-09-27**: a three-level
# browser — streams, the instants each one recorded, the facts known
# about one instant — reproducing what `aistack.cli.history_query`
# already shows, but read from the graph, so the graph is seen to
# agree with the files it was built from. Not the four richer
# maquettes already validated for the Time Machine (a time ribbon, a
# network tree, a "why" panel) — those assume data this graph does not
# hold yet (`aistack:occurredAt`, collection gaps, Explications), which
# is 1.4/1.5's own concern; building toward their visual richness now,
# ahead of that data, is exactly the invented infrastructure
# `ARC-P-006` forbids. `ADR-0011`'s own revision records this gap
# against the roadmap's four maquettes explicitly, rather than let the
# difference between what was demoed and what shipped go unstated.
REPO_ROOT = Path(__file__).resolve().parents[1]
repository = RepositoryProvider(REPO_ROOT)

GENERATED_DIR = repository.resolve(DEFAULT_GENERATED_DIR)
STORE_PATH = GENERATED_DIR / "timemachine" / "graph"

app = FastAPI(title="AIStack Time Machine")
templates = Jinja2Templates(directory=str(repository.resolve("timemachine_ui/templates")))

# One label, and whether its object is an IRI (linkable) or a literal
# (displayed as-is) — the closed set `aistack.timemachine.projection`
# actually writes today (`ADR-0011` § *Decision* 2), not a guess at
# predicates that might exist: an outgoing fact this dict does not
# know falls back to its own raw IRI, both as label and as a literal
# value, rather than a wrong guess at either.
_PREDICATE_LABELS: dict[str, tuple[str, bool]] = {
    RDF_TYPE: ("timemachine.predicate.type", True),
    PROV_GENERATED_AT_TIME: ("timemachine.predicate.generated_at", False),
    PROV_WAS_GENERATED_BY: ("timemachine.predicate.generated_by", True),
    AISTACK_STABLE_SUBJECT: ("timemachine.predicate.stable_subject", False),
    PROV_WAS_ATTRIBUTED_TO: ("timemachine.predicate.attributed_to", True),
    PROV_USED: ("timemachine.predicate.used", True),
}

_TYPE_LABELS = {
    PROV_ENTITY: "timemachine.type_label.entity",
    PROV_ACTIVITY: "timemachine.type_label.activity",
    PROV_AGENT: "timemachine.type_label.agent",
}


def _language(request: Request) -> PageLanguage:
    """ADR-0010 — same mechanism every mini-app already shares
    (`aistack.i18n.web`), tested by the governed suite even though
    this screen's own `app.py` is not (decision #9, 2026-08-29)."""

    return page_language(
        request.query_params.get(LANGUAGE_PARAMETER),
        request.cookies.get(LANGUAGE_COOKIE),
    )


def _open_store() -> OxigraphGraphStore | None:
    """The graph, read-only, or `None` when
    `aistack.cli.timemachine_rebuild` has never run against this
    `GENERATED_DIR` — a real, expected state (a fresh checkout, or a
    host where the rebuild command has not been run yet), not this
    screen's own error."""

    try:
        return OxigraphGraphStore.read_only(STORE_PATH)
    except FileNotFoundError:
        return None


def _iri_term(iri: str) -> str:
    """
    `iri` embedded as a SPARQL `IRIREF`, or `ValueError` for anything
    that could break out of the `<...>` it is embedded in. Every real
    IRI this screen ever links to came out of a previous query's own
    result — `<`/`>`/a newline in one would mean the graph itself
    holds a malformed term, not a normal request — so this is a
    defensive check, not a feature.
    """

    if not iri or any(character in iri for character in "<>\r\n"):
        raise ValueError(f"not a usable IRI: {iri!r}")
    return f"<{iri}>"


def _finish(response: HTMLResponse, language: PageLanguage) -> HTMLResponse:
    if language.cookie is not None:
        response.headers.append("set-cookie", language.cookie)
    return response


def _not_built(request: Request, language: PageLanguage) -> HTMLResponse:
    context = {"store_path": str(STORE_PATH)}
    context.update(language.context())
    return _finish(
        templates.TemplateResponse(request=request, name="not_built.html", context=context),
        language,
    )


@app.get("/", response_class=HTMLResponse)
def streams(request: Request):
    language = _language(request)
    store = _open_store()
    if store is None:
        return _not_built(request, language)

    rows = store.query(f"SELECT DISTINCT ?activity WHERE {{ ?activity a {_iri_term(PROV_ACTIVITY)} }}")
    entries = sorted(
        (
            {
                "iri": row["activity"],
                "label": stream_stem(row["activity"]) or row["activity"],
            }
            for row in rows
            if row["activity"] is not None
        ),
        key=lambda entry: entry["label"],
    )

    context: dict[str, object] = {"streams": entries}
    context.update(language.context())
    return _finish(
        templates.TemplateResponse(request=request, name="streams.html", context=context),
        language,
    )


@app.get("/node", response_class=HTMLResponse)
def node(request: Request, iri: str):
    language = _language(request)

    try:
        term = _iri_term(iri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store = _open_store()
    if store is None:
        return _not_built(request, language)

    outgoing = list(store.query(f"SELECT ?p ?o WHERE {{ {term} ?p ?o }}"))
    incoming = list(store.query(f"SELECT ?s ?p WHERE {{ ?s ?p {term} }}"))

    is_activity = any(
        row["p"] == RDF_TYPE and row["o"] == PROV_ACTIVITY for row in outgoing
    )

    instants: list[dict[str, object]] = []
    referenced_by: list[dict[str, str]] = []

    if is_activity:
        instants = [
            {
                "iri": row["entity"],
                "generated_at": row["generated_at"],
                "subject": row["subject"],
            }
            for row in store.query(
                "SELECT ?entity ?generated_at ?subject WHERE { "
                f"?entity {_iri_term(PROV_WAS_GENERATED_BY)} {term} ; "
                f"{_iri_term(PROV_GENERATED_AT_TIME)} ?generated_at . "
                f"OPTIONAL {{ ?entity {_iri_term(AISTACK_STABLE_SUBJECT)} ?subject }} "
                "} ORDER BY DESC(?generated_at)"
            )
        ]

    for row in incoming:
        if is_activity and row["p"] == PROV_WAS_GENERATED_BY:
            continue  # already shown, time-sorted, as `instants` above
        predicate = row["p"]
        label_key, _ = _PREDICATE_LABELS.get(predicate, (None, False))
        referenced_by.append(
            {"iri": row["s"], "predicate": predicate, "predicate_label_key": label_key}
        )

    facts = []
    for row in outgoing:
        predicate, obj = row["p"], row["o"]
        label_key, object_is_iri = _PREDICATE_LABELS.get(predicate, (None, False))
        object_type_label_key = (
            _TYPE_LABELS.get(obj) if predicate == RDF_TYPE else None
        )
        facts.append(
            {
                "predicate": predicate,
                "predicate_label_key": label_key,
                "object": obj,
                "object_type_label_key": object_type_label_key,
                "object_iri": obj if object_is_iri else None,
            }
        )

    node_type_label_key = next(
        (
            _TYPE_LABELS[row["o"]]
            for row in outgoing
            if row["p"] == RDF_TYPE and row["o"] in _TYPE_LABELS
        ),
        None,
    )

    context: dict[str, object] = {
        "iri": iri,
        "node_type_label_key": node_type_label_key,
        "instants": instants,
        "facts": facts,
        "referenced_by": referenced_by,
    }
    context.update(language.context())
    return _finish(
        templates.TemplateResponse(request=request, name="node.html", context=context),
        language,
    )
