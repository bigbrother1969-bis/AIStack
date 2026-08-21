"""
Selection adapters.

The selection model itself — `Selection`, `SelectionCatalog`,
`SelectionItem`, the engine and the strategies — lives in
`aistack.kernel.selection`. Import it from there.

This package holds what adapts that model to something outside
the kernel: YAML persistence, and a builder that turns a Docker
runtime catalog into a selection catalog. Neither belongs in a
kernel, and neither is a duplicate of it.

Until 2026-08-21 this file, `engine/__init__.py` and
`strategies/__init__.py` also re-exported six kernel names, which
made the package look like a second selection implementation.
Nothing in the repository imported any of the three — verified
across `src/`, `tests/`, `scripts/`, `examples/` and
`selection_ui/`, which reaches the kernel directly. A public
surface nobody consumed, shadowing the one that ships: FDN-0011
calls that an orphan implementation.

The two façade packages were removed. This file stays, without
re-exports, because `packages.find` needs it for
`aistack.selection.yaml` and `aistack.selection.from_docker_catalog`
to be packaged at all.
"""
