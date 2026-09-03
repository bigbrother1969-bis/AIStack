"""
Application definition adapters.

The model itself — `ApplicationDefinition`, `SyncthingDefinition`
— lives in `aistack.kernel.application`. Import it from there.

This package holds what adapts that model to something outside
the kernel: YAML persistence, mirroring `aistack.catalog.yaml` and
`aistack.selection.yaml`. This file stays, without re-exports,
because `packages.find` needs it for `aistack.application.yaml` to
be packaged at all.
"""
