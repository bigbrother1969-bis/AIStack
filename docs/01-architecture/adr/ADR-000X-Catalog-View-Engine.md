# ADR-000X - Catalog View Engine

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

