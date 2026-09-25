---
artifact:
  id: FDN-0009
  title: AI Collaboration Protocol
  type: Foundation Protocol
  semantic_type: Policy
  domain: Foundation
  criticality: C3
  version: 1.2
  status: Published
  confidence: Reviewed
  owner: Foundation
  created: 2026-07-06
  updated: 2026-09-25

relations:
  references:
    - FDN-0002
    - FDN-0003
    - FDN-0005
    - FDN-0008
    - FDN-0012
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

**Gravé** is defined in `FDN-0002` (*Glossary*, § *Gravé*), the term's
Single Point Of Truth since 2026-09-25. Its lifecycle position is
Validated → **Gravé** → Published → Distributed (`FDN-0005` §
*Knowledge Lifecycle*).

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

Human validation remains mandatory for every governance decision. Per GOV-P-001,
the AI never creates authoritative knowledge.

---

## Protocol Improvement

When a collaboration failure is observed and a better practice is validated,
this protocol shall be updated, so that the same failure does not recur in a
later session.

Improvements follow the same governed cycle as any other artifact. The protocol
is subject to the rules it describes.

**Recorded 2026-09-25, `GOV-0002/OS-072`.** Three failures observed during
the `STD-0300` § 2.4 cross-model comparison (2026-09-23), each with the
practice the owner validated against it:

1. **Freshness asserted from outside the bundle.** A Boot Report stated the
   bundle was current on the strength of a claim made in conversation, not
   of the bundle's own `generated_at`/`source_commit`. `OPS-0002` already
   states that a recipient who cannot reach the repository cannot decide
   freshness and should say so rather than assume — this protocol had
   never stated the same rule for the AI's own output. **Practice**: an AI
   stating a bundle's freshness or currency states it from the bundle's
   own generation timestamp and source commit alone; a freshness claim
   made by the human, a prior session, or any source outside the bundle
   is not evidence of it, and is named as an unverified claim if repeated
   at all.
2. **A self-generated uncertainty presented as heritage-declared.** The
   four states in § *Uncertainty in Collaboration* were not kept distinct
   in practice: an uncertainty the AI itself had produced (`Proposed`)
   was worded as though the heritage had declared it absent (`Unknown`).
   **Practice**: an AI reporting an uncertainty names which of the four
   states it occupies, in those words, rather than in a form of words
   that reads as `Unknown` for what is in fact `Proposed`.
3. **Flagged before reading the register.** A discrepancy was reported as
   a new finding before `GOV-0002`'s *Decisions* and *Resolved* sections,
   or an artifact's own *Implementation state* table, were checked for
   whether the condition was already qualified there. **Practice**:
   before reporting a gap or discrepancy as a finding, an AI reads
   `GOV-0002` and any *Implementation state* table the artifact under
   review carries. From 2026-09-25 the `declared-unknowns` check
   (`GOV-0002/OS-071`) assists this for the markers this heritage already
   uses to declare an unknown, but does not replace reading the register
   for what a marker does not cover.

---

## Open Point

FDN-0002 declares itself the Single Point Of Truth for AIStack terminology, yet
**Gravé** — the central term of principle GOV-P-004 — is defined in FDN-0005 and
not in the Glossary. This document deliberately does not add a fourth definition.
Consolidating the term into FDN-0002 is left as a governed decision.

**Resolved 2026-09-25 by the owner, `GOV-0002/OS-061`.** `FDN-0002` §
*Gravé* is now the term's SPOT. `FDN-0005` § *Vocabulary* points to it
rather than restating it, and § *The Gravé Transaction* above cites
`FDN-0002` instead. This paragraph is kept rather than deleted, per
`GOV-0002` § *What a closure must carry*: it is what first named the
gap, dated 2026-08-21, 35 days before it closed.
