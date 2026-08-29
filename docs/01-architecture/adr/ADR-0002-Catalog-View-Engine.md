---
artifact:
  id: ADR-0002
  title: Catalog View Engine
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.5
  status: Accepted
  owner: Architecture
  created: 2026-07-07
  updated: 2026-08-29
---

# ADR-0002 - Catalog View Engine

## Status

Accepted

## Context

AIStack providers produce raw observations.

These observations are normalized into the Infrastructure Data Catalog.

The Infrastructure Data Catalog is exhaustive by design.

However, most downstream components do not need the full catalog.

Selection workflows, user interfaces, reports, diagnostics and assisted actions require purpose-specific representations of catalog data.

The first Selection Engine implementation revealed this need clearly.

The Selection Engine should not consume the raw Infrastructure Data Catalog directly.

It should consume a governed Catalog View.

---

## Decision

AIStack introduces the concept of **Catalog View**.

A Catalog View is a governed, purpose-specific representation derived from the Infrastructure Data Catalog.

The Catalog View Engine is responsible for producing these views.

The generic flow becomes:

    Knowledge Provider
            │
            ▼
    Raw Observation
            │
            ▼
    Infrastructure Data Catalog
            │
            ▼
    Catalog View Engine
            │
            ▼
    Selection Engine / UI / Reports / Actions

---

## Principles

The Infrastructure Data Catalog remains exhaustive.

Catalog Views are contextual.

A Catalog View shall be:

- derived from the Infrastructure Data Catalog;
- reproducible;
- traceable to its source catalog;
- limited to the purpose it serves;
- suitable for downstream consumers.

The Selection Engine consumes Catalog Views, never raw provider observations.

---

## Rationale

The Infrastructure Data Catalog is the canonical inventory of the infrastructure.

A Catalog View is an operational projection of that inventory.

This separation prevents downstream components from depending on provider-specific formats or exhaustive catalog structures.

It allows AIStack to expose different governed representations of the same infrastructure according to the intended use.

Example:

A Docker Runtime Catalog may contain:

- container identifiers;
- images;
- labels;
- ports;
- networks;
- mounts;
- health status;
- runtime metadata.

A Docker Container Selection View only exposes:

- name;
- image;
- state;
- display metadata.

---

## Implementation state

Measured 2026-08-28 at `1174078`. **Every part of the concept exists, and no
path that runs produces a Catalog View.**

| Step | State |
|---|---|
| `CatalogView` — the governed, purpose-specific representation | done — 2026-08-28 |
| `CatalogViewEngine` — the contract that produces one, `build(Catalog) -> CatalogView` | done — 2026-08-28 |
| One Catalog View Engine — `MusicSelectionViewEngine` | done — 2026-08-28 |
| A Catalog View is derived from a catalog and traceable to it | done — 2026-08-28 |
| A Catalog View is reproducible | done — 2026-08-28 |
| A Catalog View is limited to the purpose it serves | done — 2026-08-28 |
| The Selection Engine consumes a Catalog View, never a raw provider observation | done — 2026-08-28 |
| Infrastructure Data Catalog → Catalog View Engine → consumer, on a path that runs | done — 2026-08-29 |
| The Selection UI as the first Catalog View consumer | done — 2026-08-29 |

What each was read against:

| Step | Evidence |
|---|---|
| `CatalogView` | `src/aistack/kernel/catalog/views/core.py` — `CatalogView(view_id, source_catalog_id, title, items, metadata)` and `CatalogViewItem(id, label, metadata)`, both frozen |
| `CatalogViewEngine` | `src/aistack/kernel/contracts/catalog_view.py`, exported by `kernel/contracts/__init__.py`; `CatalogViewRegistry` is `Registry[CatalogViewEngine]`, and ARCH-0007 § *Current Registries* names it |
| the engine | `src/aistack/catalog/views/music/selection.py`, registered as `music-selection` by `kernel/bootstrap/catalog_views.py` |
| derived and traceable | `build` takes the `Catalog`, and the view it returns sets `source_catalog_id` from `catalog.catalog_id` |
| reproducible | `MusicSelectionViewEngine.build` reads no clock, no file and no environment: its result is a function of its argument. Read off the one implementation — **nothing verifies it for the next one** |
| limited to its purpose | `CatalogItem` carries `id`, `label`, `kind`, `source`, `metadata`; `CatalogViewItem` carries `id`, `label`, `metadata`, and the one engine moves `kind` and `source` into `metadata`. **It drops nothing** — qualified `done` by the owner on 2026-08-28, see below |
| the Selection Engine's input | `SelectionEngine.select(view: CatalogView, …)` and `SelectionStrategy.select(view: CatalogView)`. The type is the guarantee: no provider observation reaches either |
| the flow | `aistack.cli.docker_selection_catalog`, and the five tests of `tests/unit/cli/test_the_provider_commands_run.py` that drive it — below |
| the Selection UI | `selection_ui/app.py` builds a view through `aistack.selection.workflow`, and six tests drive that workflow — below |

### The flow, closed 2026-08-29

`aistack.cli.docker_selection_catalog` runs it end to end:

```text
providers.get("docker").collect()
    → DockerRuntimeCatalogBuilder.build(observation) -> Catalog
    → registries.catalog_views.get("docker-containers").build(catalog) -> CatalogView
    → CatalogViewArtifactGenerator.generate(view, path)
```

**Three things had to be true at once, and none of them was.** The builder
returned a `dict` where a Catalog View Engine takes a `Catalog`; the live path
built a `SelectionCatalog`, a v0 type satisfying no contract (GOV-0002/OS-042,
qualified 2026-08-29); and the command itself raised on its second line and had
since 2026-08-20 (GOV-0002/OS-044). *A row can be `not implemented` for more
than one reason at a time, and this one was for three.*

**The engine is retrieved from the registry by identifier**, not instantiated.
That is what makes the producer governed knowledge rather than a class named in
a command — and it gives `catalog_views` its first read site.

*The artifact goes through an Artifact Generator, which the retired path did
not: it serialised with `write_text` and a `default=lambda item: item.__dict__`
hook. `CatalogViewArtifactGenerator` is generic, because a Catalog View names no
technology.*

### The consumer, closed 2026-08-29

`selection_ui` displayed `catalog.items` and built its `Selection` by hand,
passing through no view, no engine and no strategy. It now does both through the
Kernel:

```text
index  load_catalog_yaml → build_view(kernel, catalog, definition["view_id"]) → template
save   build_view(...) → select_from_view(view, app_id, ticked_ids) → save_selection_yaml
```

**The engine that had waited for this is the one that existed.** `music-selection`
was registered from the day the registry existed and retrieved by nothing; the
screen it was written for was building its own list beside it.

**Which view a screen shows is governed data.** `view_id: music-selection` is
declared in the application definition, not named in application code — the same
rule the Docker path follows by retrieving `docker-containers` by identifier.

**The logic is not in the HTTP handler**, and that is a packaging fact rather
than taste. `selection_ui` is a top-level package whose dependencies —
`fastapi`, `starlette`, `jinja2` — this project does not declare: `pyproject.toml`
declares `PyYAML` and nothing else. Testing the handlers would mean adding
dependencies to the heritage, which ADR-0001 governs. `aistack.selection.workflow`
holds the chain, six tests drive it, and each handler is two lines. *ADR-0003's
delegation is exercised for the first time: the engine holds a strategy and no
criterion, and a stale identifier is dropped by the strategy rather than carried
into governed knowledge — which the hand-built `Selection` did not do.*

**Two things were repaired in passing, and neither had an instrument.**
`ByIdsSelectionStrategy.select` returned `list[str]` while its Protocol declared
`tuple[str, ...]` — recorded by ADR-0003 on 2026-08-27 and left, correctly,
because nothing consumed the chain. And the `by-ids` registration held
`ByIdsSelectionStrategy([])`: an instance selecting nothing, under a name nobody
could use, because the strategy carries its identifiers in its constructor.
Removed by the owner on 2026-08-29. *Neither `contract-debt` nor
`false-declarations` sees a return type; both compare call shapes.*

### The report got quieter, and not only because things improved

Measured 2026-08-29, after this row closed:

```text
unused-registrations   0 registered identifiers retrieved by nothing (was 2)
unused-registrations   2 of 4 registries empty after bootstrap (was 1)
unused-registrations   2 retrieval sites name a computed identifier (was 1)
```

**The first line is not the whole truth.** `music-selection` is no longer
reported as unretrieved — but the reason is that `catalog_views` now carries a
**computed** retrieval site, `catalog_views.get(view_id)`, and the check excludes
a registry it cannot resolve statically. Making the view identifier governed data
is what put it there. *The instrument reports less because it can see less, and
what actually establishes the retrieval is a test —
`test_the_view_is_produced_by_an_engine_retrieved_by_identifier` — not the
report.*

**The second line is a true statement newly published.** `selection_strategies`
is empty because nothing belongs in it, which is a decision and is recorded in
`kernel/bootstrap/default.py`; `tasks` is empty because GOV-0002/OS-041's work
has not been done. **A report cannot tell those two apart**, which is why both
are written down where a reader will meet them.

### The engine was registered and never retrieved

Measured across the whole repository on 2026-08-28, excluding `archive/` — and
this is the state the row above was closed *out of*, kept because a decision
that erased what it looked like before cannot show that anything moved:

```text
kernel.registries.catalog_views    → 1 write site, 0 read sites
MusicSelectionViewEngine           → 1 instantiation, in bootstrap; 0 callers
CatalogViewEngine.build            → 0 call sites
tests exercising a Catalog View    → 0
```

The last line is measured rather than inferred: `tests/unit/catalog/views/test_imports.py`
is the only test that names these types, and it asserts that three of them are
not `None`.

This was GOV-0002/OS-039 one layer up. That entry records that `SelectionEngine`
has no caller; the engine that would build what it consumes had none either, and
the registry that would hand it over was written to once and read never.

**All of it closed on 2026-08-29**, in two commits and in that order: the
producer first — a command builds a Catalog View through a registered engine —
then the consumer, when the Selection UI began retrieving `music-selection` and
selecting through the engine. **Producing a view is not consuming one**, and the
two were separate rows because they were separate absences.

### The path that runs builds a second view type

`docker_selection_catalog` produces the very thing § *Rationale* uses as its
example — a Docker container selection view exposing name, image, state and
display metadata. It does not pass through this decision:

```text
docker provider → DockerRuntimeCatalogBuilder → dict
               → DockerSelectionCatalogBuilder → SelectionCatalog → JSON
```

- the Docker runtime catalog is a `dict`. `ComposeRuntimeCatalogBuilder.build`
  returns a `Catalog`; the two builders sit side by side under
  `src/aistack/catalog/` and do not return the same kind of thing;
- `DockerSelectionCatalogBuilder.build(dict) -> SelectionCatalog` does not
  satisfy `CatalogViewEngine`, and is registered in no registry;
- `SelectionCatalog`, in `kernel/selection/core.py`, is documented as *"Catalog
  view exposed to a selection workflow"* and carries `catalog_id`, `title`,
  `items`, `metadata`, over `SelectionItem(id, label, metadata)` — field for
  field, `CatalogView` and `CatalogViewItem` under other names.

**So the concept this decision governs exists twice**: once as the governed type
that nothing running produces, once as the type the running path produces. Which
of the two is the Catalog View is not derivable from the code — both readings
are coherent — and it is left as an open row here rather than answered, because
answering it is a decision and not a measurement. **GOV-0002/OS-042** holds the
question, opened 2026-08-28 with the three readings that were live that day.

### The row that measured badly and was qualified anyway

**A Catalog View is limited to the purpose it serves** was left `unqualified` on
the measurement above: the one engine narrows nothing. **The owner qualified it
`done` on 2026-08-28**, and the reading is that a view is a purpose-oriented
*re-shaping* rather than a subtraction. `MusicSelectionViewEngine` reads a music
catalogue whose items carry nothing a selection does not need, so there is
nothing to drop and dropping nothing is the correct output.

*The argument that was declined is on the record, because it is not weak.*
§ *Rationale* illustrates the principle with the opposite case — a Docker
runtime catalogue of eight fields against a selection view of four — and under
that reading the principle is about subtraction and the one existing engine does
not honour it. What settles it is that the principle constrains the **view**,
not the engine: a view limited to its purpose is one that carries what the
purpose needs, and whether that is fewer fields depends on the catalogue.

**The row is therefore closed on a decision and not on a measurement**, and it
says so. What the measurement establishes is that this heritage has one engine
over one catalogue, and that the case the § *Rationale* draws its example from
is the one no engine builds — which is a different row of this table.

### What is not a row

§ *Consequences* lists nine future Catalog Views — Docker container, volume and
network selection, filesystem, Syncthing, backup scope, service remediation,
documentation generation scopes, assisted action scopes. It lists them under
*may support*. They illustrate what the concept opens; reading them as
requirements would put nine rows in this table that this decision never
committed to. That is the reading error ADR-0001 § *Implementation state*
records for its own decisions 2 and 4.

*The Infrastructure Data Catalog remains exhaustive* and *Catalog Views are
contextual* are likewise not rows: the first is a property of the catalog this
decision does not change, the second is the definition of the term.

The first consequence — *the Selection Engine becomes completely generic* — is a
row of ADR-0003, `done` there, measured 2026-08-27. It is not restated here.

---

## Consequences

The Selection Engine becomes completely generic.

The existing Selection UI is reinterpreted as the first implementation of a Catalog View consumer.

Future Catalog Views may support:

- Docker container selection;
- Docker volume selection;
- Docker network selection;
- Filesystem selection;
- Syncthing synchronization;
- Backup scope selection;
- Service remediation selection;
- Documentation generation scopes;
- Assisted action scopes.

This validates that the historical Selection UI was not a temporary tool.

It was an early implementation of a generic architectural concept.

