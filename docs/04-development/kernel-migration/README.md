# Kernel Migration

## Objective

Kernel Migration is the incremental migration of generic AIStack concepts into the technology-independent Kernel.

The objective is to align the source tree with the AIStack Kernel Architecture ADR.

## Rule

Generic concepts belong to the Kernel.

Technology-specific implementations belong outside the Kernel.

Implementations of Kernel contracts belong in implementation-specific packages.

## Migration Order

1. Move Catalog core concepts into kernel/catalog.
2. Move Catalog View core concepts into kernel/catalog/views.
3. Move Selection core concepts into kernel/selection.
4. Move Selection Engine into kernel/selection/engine.
5. Move Selection Strategies contracts into kernel/selection/strategies.
6. Create kernel/contracts for stable Protocols.
7. Update imports incrementally.
8. Validate after each migration step.

## Constraints

- Never leave a migration half-finished.
- Each migration step shall be atomic.
- Each migration step shall compile.
- Each migration step shall preserve existing behavior.
- Operational artifacts shall not be modified during migration tests.

## Validation Case

The Music/Syncthing selection workflow is the reference validation case for Kernel Migration.

Each migration step shall preserve this pipeline:

    Music Catalog YAML
        -> Catalog
        -> Catalog View
        -> Selection Engine
        -> Selection Strategy
        -> Selection YAML test artifact
