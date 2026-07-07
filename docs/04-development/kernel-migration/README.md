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

---

# Migration Completion Report

## Status

Completed

## Summary

The first Kernel Migration workstream has been completed successfully.

The migration progressively moved generic concepts from technology-oriented packages into the technology-independent Kernel while preserving backward compatibility throughout the process.

Each migration step was performed as an atomic change, compiled independently and validated using the production Music/Syncthing workflow.

## Migrated Concepts

- Catalog
- Catalog View
- Selection
- Selection Engine
- Selection Strategies
- Kernel Contracts
- Kernel Registry
- Kernel Registries
- Kernel Context

## Validation

The migration was validated after every step using the same governed workflow:

    Music Catalog YAML
        -> Catalog
        -> Catalog View
        -> Selection Engine
        -> Selection Strategy
        -> Selection YAML

The generated Selection artifact remained identical throughout the migration.

No regression was observed.

## Lessons Learned

The migration demonstrated that generic concepts can be extracted incrementally without disrupting operational workflows.

The migration procedure itself became standardized:

1. Move the generic concept.
2. Search every remaining import.
3. Update imports.
4. Compile.
5. Execute the production validation case.
6. Compare generated artifacts.
7. Verify a clean Git status.
8. Commit an atomic migration.

This procedure is now the recommended migration methodology for future Kernel refactoring.

## Result

AIStack now possesses a stable, technology-independent Kernel centered on governed concepts rather than infrastructure technologies.

This Kernel provides the foundation for future Provider plugins, Context loading, Self-Onboarding and the Knowledge Operating System architecture.
