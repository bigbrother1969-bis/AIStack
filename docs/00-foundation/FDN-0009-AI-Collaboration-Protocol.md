---
artifact:
  id: FDN-0009
  title: AI Collaboration Protocol
  type: Foundation Protocol
  criticality: C3
  version: 1.0
  status: Published
  confidence: Reviewed
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-21

relations:
  references:
    - FDN-0002
    - FDN-0003
    - FDN-0005
    - FDN-0008
    - PRINCIPLES-REGISTRY
---

# FDN-0009 — AI Collaboration Protocol

## Purpose

This document defines how an AI model shall collaborate with a human on AIStack.

It governs collaboration mechanics — how a validated decision becomes a governed
artifact. It does not govern knowledge acquisition, which belongs to the AI Boot
section of the README.

The protocol is not a prompt. It is a governed component of the Knowledge
Operating System, and it evolves through explicit validation like any other
Knowledge Artifact.

---

## Provenance

This artifact restores `context/AI_PROTOCOL.md`, which was removed from the
heritage on 2026-07-31 by commit `76bd373` — a context-bundle refactoring whose
message did not mention it. The removal was collateral, not a decision.

Three changes were made during restoration:

- the definition of **Gravé**, previously stated three times in the same
  document, is stated once;
- the Knowledge Uncertainty section references FDN-0003 Article 12 instead of
  restating it, that article having been adopted after this document was written;
- the reference to `AI_TRANSACTION_PROTOCOL.md` is dropped — that artifact is
  declared obsolete and is deliberately not restored.

**Gravé — 2026-08-21.** This artifact is governed heritage. What is engraved is a
*restoration*: the wording comes from `76bd373^:context/AI_PROTOCOL.md`, and the three
changes listed above — the deduplication of *Gravé*, the reference to Article 12, the
dropped reference to a non-existent artifact — were made by an AI assistant and
accepted by the owner. `confidence: Reviewed`: read and accepted, not verified against
the original by a third party.

---

## The Gravé Transaction

**Gravé** is defined in FDN-0005 (*Project Operating Model*): the idea shall
become part of the official Governed Heritage. Its lifecycle position is
Validated → **Gravé** → Published → Distributed.

When the human writes *Gravé*, the AI shall:

1. identify the appropriate governed SPOT;
2. choose the safest update strategy — create, append, targeted update or
   replacement;
3. generate a complete executable documentation transaction;
4. preserve the official terminology of FDN-0002;
5. provide the validation commands;
6. provide the required Git commands.

The AI shall never answer a *Gravé* with an acknowledgement alone.

*Gravé* never denotes a conversational agreement or a temporary note. It always
denotes permanent integration into the governed heritage.

---

## Command Generation Policy

The human shall never be expected to manually copy and paste text into project
files.

Whenever a governed artifact must be created or modified, the AI shall generate
complete executable command sequences — file creation, update, append,
replacement, directory creation and Git operations.

The objective is to eliminate typing and syntax errors, guarantee
reproducibility, reduce cognitive load, and keep the workflow deterministic.

Knowledge is transmitted through deterministic executable commands rather than
manual editing.

---

## Uncertainty in Collaboration

FDN-0003 Article 12 governs knowledge uncertainty. This protocol states its
operational consequences for an AI assistant.

When the AI cannot find an answer in governed sources, it shall state that the
knowledge was not found. It shall not substitute a plausible assumption.

**Similarity, correlation or semantic proximity shall never be treated as
validation.**

The AI shall keep four states distinct and never let one pass for another:

| State | Meaning |
|---|---|
| Known | present in the governed heritage |
| Unknown | absent from the governed heritage, and declared as such |
| Proposed | produced by the AI, awaiting human validation |
| Validated | accepted by the human, pending *Gravé* |

Human validation remains mandatory for every governance decision. Per GOV-001,
the AI never creates authoritative knowledge.

---

## Protocol Improvement

When a collaboration failure is observed and a better practice is validated,
this protocol shall be updated, so that the same failure does not recur in a
later session.

Improvements follow the same governed cycle as any other artifact. The protocol
is subject to the rules it describes.

---

## Open Point

FDN-0002 declares itself the Single Point Of Truth for AIStack terminology, yet
**Gravé** — the central term of principle GOV-004 — is defined in FDN-0005 and
not in the Glossary. This document deliberately does not add a fourth definition.
Consolidating the term into FDN-0002 is left as a governed decision.
