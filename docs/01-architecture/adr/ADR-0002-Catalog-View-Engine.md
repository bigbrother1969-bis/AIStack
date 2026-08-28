---
artifact:
  id: ADR-0002
  title: Catalog View Engine
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.1
  status: Accepted
  owner: Architecture
  created: 2026-07-07
  updated: 2026-08-28
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
| A Catalog View is limited to the purpose it serves | unqualified — 2026-08-28 |
| The Selection Engine consumes a Catalog View, never a raw provider observation | done — 2026-08-28 |
| Infrastructure Data Catalog → Catalog View Engine → consumer, on a path that runs | not implemented — measured 2026-08-28 |
| The Selection UI as the first Catalog View consumer | not implemented — measured 2026-08-28 |

What each was read against:

| Step | Evidence |
|---|---|
| `CatalogView` | `src/aistack/kernel/catalog/views/core.py` — `CatalogView(view_id, source_catalog_id, title, items, metadata)` and `CatalogViewItem(id, label, metadata)`, both frozen |
| `CatalogViewEngine` | `src/aistack/kernel/contracts/catalog_view.py`, exported by `kernel/contracts/__init__.py`; `CatalogViewRegistry` is `Registry[CatalogViewEngine]`, and ARCH-0007 § *Current Registries* names it |
| the engine | `src/aistack/catalog/views/music/selection.py`, registered as `music-selection` by `kernel/bootstrap/catalog_views.py` |
| derived and traceable | `build` takes the `Catalog`, and the view it returns sets `source_catalog_id` from `catalog.catalog_id` |
| reproducible | `MusicSelectionViewEngine.build` reads no clock, no file and no environment: its result is a function of its argument. Read off the one implementation — **nothing verifies it for the next one** |
| limited to its purpose | `CatalogItem` carries `id`, `label`, `kind`, `source`, `metadata`; `CatalogViewItem` carries `id`, `label`, `metadata`, and the one engine moves `kind` and `source` into `metadata`. **It drops nothing** |
| the Selection Engine's input | `SelectionEngine.select(view: CatalogView, …)` and `SelectionStrategy.select(view: CatalogView)`. The type is the guarantee: no provider observation reaches either |
| the flow | measured across the repository — below |
| the Selection UI | `selection_ui/app.py` imports `load_catalog_yaml`, `Selection`, `load_selection_yaml` and `RepositoryProvider`. It never names `CatalogView` |

### The engine is registered and never retrieved

Measured across the whole repository on 2026-08-28, excluding `archive/`:

```text
kernel.registries.catalog_views    → 1 write site, 0 read sites
MusicSelectionViewEngine           → 1 instantiation, in bootstrap; 0 callers
CatalogViewEngine.build            → 0 call sites
tests exercising a Catalog View    → 0
```

The last line is measured rather than inferred: `tests/unit/catalog/views/test_imports.py`
is the only test that names these types, and it asserts that three of them are
not `None`.

This is GOV-0002/OS-039 one layer up. That entry records that `SelectionEngine`
has no caller; the engine that would build what it consumes has none either,
and the registry that would hand it over is written to once and read never.

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
of the two is the Catalog View is not derivable from the code — both are
coherent — and no artifact records the question. It is left as an open row here
rather than answered, because answering it is a decision and not a measurement.

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

