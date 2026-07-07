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

---

# First AI Runtime Validation Case

## Objective

The first complete validation case for the AI Runtime shall focus on a real engineering problem:

    "How can I improve my Technical Debt Score?"

## Why this use case

This use case exercises almost every major subsystem of the Knowledge Operating System while remaining completely grounded in governed knowledge.

It demonstrates the complementary roles of the deterministic Runtime and the AI Runtime.

## Deterministic Runtime Responsibilities

The deterministic Runtime shall:

- discover the infrastructure;
- build governed Catalogs;
- evaluate Knowledge Policies;
- compute the Technical Debt Score;
- produce evidence and traceability.

These results constitute the Single Point Of Truth.

## AI Runtime Responsibilities

The AI Runtime shall never compute the score itself.

Instead it shall:

- explain the score;
- identify the major contributors;
- explain the governing policies involved;
- prioritize remediation actions;
- estimate expected improvements;
- generate a draft improvement plan;
- answer follow-up engineering questions.

## Validation Goal

The complete workflow shall become:

    discover
        -> catalog
        -> evaluate
        -> compute Technical Debt Score
        -> reason
        -> explain
        -> recommend
        -> draft improvement plan

This validation shall demonstrate that AIStack uses AI to reason about governed knowledge rather than to replace governed knowledge.

---

# AI Knowledge Grounding from Context Bundles

## Objective

The fourth Runtime validation workstream shall focus on building a governed AI knowledge base from AIStack Context Bundles and generated documentation.

## Principle

AI engines shall reason on governed knowledge rather than on raw infrastructure observations.

The Runtime remains responsible for producing governed knowledge.

The AI Runtime becomes responsible for consuming this governed knowledge.

## Runtime Responsibilities

The Runtime shall produce:

- Context Bundles;
- generated documentation;
- Knowledge Artifacts;
- governed metadata;
- provenance information;
- traceability information.

These outputs constitute the knowledge corpus made available to AI engines.

## AI Runtime Responsibilities

The AI Runtime shall:

- ingest Context Bundles;
- ingest generated documentation;
- build Knowledge Chunks;
- build searchable indexes;
- preserve provenance;
- preserve traceability;
- support local Retrieval-Augmented Generation (RAG);
- evaluate answer quality.

The AI Runtime shall never modify governed knowledge.

## Architecture Principle

Git remains the Single Point Of Truth.

Context Bundles are transferable governed knowledge.

AI indexes are disposable runtime artifacts regenerated from governed sources.

Changing an AI model shall never require rebuilding the governed knowledge base.

## Long-term Goal

Any compatible AI Engine (Ollama today, another implementation tomorrow) shall become operational simply by ingesting the governed Context Bundles produced by AIStack.

This demonstrates the portability of the Knowledge Operating System independently of any specific AI technology.
