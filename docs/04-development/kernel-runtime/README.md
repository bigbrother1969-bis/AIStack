# Kernel Runtime Operations

## Status

Draft

## Initial Runtime Operations

- boot: initialize the Runtime through KernelBootstrap.
- discover: collect observations from Knowledge Providers.
- catalog: transform observations into governed Catalogs.
- view: build Catalog Views from Catalogs.
- select: apply Selection Strategies.
- evaluate: apply Knowledge Policies and governance rules.
- generate: produce deterministic artifacts from governed knowledge.
- render: produce human-readable views, reports and dashboards.
- export_bundle: export a governed transferable context bundle.
- run: orchestrate a complete configured pipeline.

## Initial Implementation Order

1. discover
2. catalog
3. generate
4. export_bundle
5. run

## Future AI Engine Operations

After the first Runtime operations are stabilized, AIStack shall define operations related to local AI modules, especially Ollama-based engines.

These operations shall respect the AIStack principle: AI is a reasoning assistant, never a source of truth.

Potential future operations include:

- reason
- explain
- summarize
- recommend
- validate_with_context
- generate_draft_artifact

Ollama integration shall be treated as a replaceable AI Engine implementation behind governed Kernel contracts.
