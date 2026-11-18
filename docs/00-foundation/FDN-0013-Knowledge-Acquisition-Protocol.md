---
artifact:
  id: FDN-0013
  title: Knowledge Acquisition Protocol
  type: Foundation Protocol
  semantic_type: Policy
  domain: Foundation
  confidence: Declared
  criticality: C3
  version: 0.2
  status: Draft
  owner: Foundation
  created: 2026-11-17
  updated: 2026-11-18

relations:
  references:
    - FDN-0002
    - FDN-0003
    - FDN-0008
    - FDN-0009
    - FDN-0012
---

# FDN-0013 — Knowledge Acquisition Protocol

## Purpose

This document defines how an agent acquires governed knowledge before it
reasons.

The Knowledge Acquisition Protocol (KAP) answers one question: *how does an
agent acquire governed knowledge before reasoning?* It does not answer how an
agent collaborates with a human once it has acquired it (`FDN-0009`), nor how
knowledge is governed (`FDN-0003`).

The protocol is technology-independent. It does not depend on AIStack's code,
on the Context Bundle's file format, or on any model. What implements it, and
what carries the knowledge, are named in § *What implements it*, and can change
without this text changing.

**Status of this version.** `Draft`, written 2026-11-17 by an AI assistant at the
owner's request (decision of 2026-11-17, `ADR-0027` § 13). Per `GOV-P-001`, an AI
assistant creates no authoritative knowledge: the text below is *Proposed* in the
sense of `FDN-0009` until the owner validates it and it is engraved (*Gravé*). It
is assembled from what the heritage already states — the August 2026 refactoring
plan (phases 4 and 5), the two Boot Reports of 2026-08-13 and 2026-09-23, the
practices recorded in `FDN-0009` (`GOV-0002/OS-072`) and the criteria of
`STD-0300` § VS-2. Where it adds a rule that none of them states, § *Open points*
says so.

---

## Principles

1. **Knowledge before reasoning.** An agent reads before it concludes. A
   conclusion that precedes the acquisition it depends on is not evidence.
2. **Governed knowledge first.** What the governed heritage states prevails over
   what the agent knows from elsewhere, and over what it is told in conversation.
3. **Explicit uncertainty.** What is absent is declared absent, never replaced by
   a plausible assumption (`FDN-0003` Article 12). Similarity is not validation.
4. **Explainability.** Every statement of the agent cites the artifact that
   carries it.
5. **Reproducibility.** Two agents given the same bundle follow the same
   acquisition and produce the same report. They may differ in the quality of
   their reasoning, never in how they started.

---

## The two points of truth

| Role | What it is | The question it answers |
|---|---|---|
| **Governance SPOT** | the reference repository | *where is the official governed knowledge?* |
| **Acquisition SPOT** | the Context Bundle, a projection of the repository | *what is the official portable representation of it?* |

The bundle is explicitly not the Governance SPOT: it carries a `source_commit` and
a `content_hash`, and a mirror of the repository is not authoritative
(`OPS-0002`). An agent that holds only the bundle acquires from the bundle and
says so.

**Freshness is read from the bundle.** An agent states how current a bundle is
from its own `generated_at` and `source_commit` alone. A claim of freshness made
in conversation, by the human or by an earlier session, is not evidence of it
(`FDN-0009`, practice 1 of `GOV-0002/OS-072`).

---

## Acquisition states

An agent moves through the states in order. A state is *reached* when the agent
has read the artifacts that carry what the state names; it is *partial* when it
has read some of them and says which are missing.

| State | What it acquires |
|---|---|
| **UNINITIALIZED** | nothing: the bundle has not been read |
| **IDENTITY ACQUIRED** | what the project is, its purpose and licence, its language, which repository is the Governance SPOT and which projection the Acquisition SPOT |
| **VOCABULARY ACQUIRED** | the official terms and their SPOT (`FDN-0002`) |
| **GOVERNANCE ACQUIRED** | the Constitution, the registered principles (`FDN-0012`), how knowledge is validated and engraved |
| **ARCHITECTURE ACQUIRED** | the structure the code and the decisions give the product, and the state of each decision's implementation |
| **OPERATIONAL CONTEXT ACQUIRED** | what is open, decided and resolved now (`GOV-0002`), and the state of the validation suite (`STD-0300`) |
| **READY** | the agent can reason on the project, within the scope it declares |

**Acquisition is selective, not exhaustive.** The objective is not to load the
whole heritage. The agent classifies every artifact from its declared metadata,
reads in full what the states above require, and names what it sampled rather
than read, since that bounds what its report can answer.

---

## What the protocol produces

The protocol produces an **Operational Context**: what the agent now holds, with
its provenance and its limits. It produces no recommendation. A recommendation is
reasoning, and reasoning starts after READY.

The Operational Context is written down as a **Boot Report**.

---

## The Boot Report

Every agent produces the same report, in eight sections. An agent that omits one
has not produced a Boot Report (`STD-0300` § VS-2, criterion 2.1).

| # | Section | It states |
|---|---|---|
| 1 | **Identity** | what the project is, from which artifacts; the bundle read: its `id`, `generated_at`, `source_commit`, `content_hash` and the number of artifacts |
| 2 | **Vocabulary** | the terms the agent relies on and whether the Glossary defines each |
| 3 | **Governance** | the principles and the lifecycle that bind the agent's work |
| 4 | **Architecture** | the structure, and the implementation state of what was decided |
| 5 | **Operational Context** | what is open, decided and resolved, from `GOV-0002` and the validation suite |
| 6 | **Known Uncertainties** | each uncertainty, with the state it occupies (below) |
| 7 | **Integrity Warnings** | each finding of the integrity check, with its severity, and any the agent found by reading |
| 8 | **READY / NOT READY** | the verdict, its scope, and what it rests on |

A report also carries, before section 1, an **acquisition trace**: the state
reached, and the artifacts consumed for each.

**Each uncertainty names its state**, in the words of `FDN-0009`: *Known*,
*Unknown*, *Proposed* or *Validated*. An uncertainty the agent produced itself is
*Proposed*; it is never worded as one the heritage declared (*Unknown*)
(`FDN-0009`, practice 2). Before reporting a discrepancy as a finding, the agent
reads `GOV-0002` and the implementation-state table of the artifact concerned, to
see whether the condition is already qualified (practice 3). The uncertainties
the heritage declares itself, by its own markers (*Open Point*, `grounding:
unknown`, *not verified*, *recorded as lost*, *pending*, and the like), are
extracted by the `declared-unknowns` check; an agent covers them, and adds
nothing that `GOV-0002` already qualifies (`STD-0300` § VS-2, criterion 2.4).

**Integrity warnings come from the check, not from the agent's impression.** The
integrity check reads the bundle (`aistack.cli.knowledge_integrity`) and reports
what it observed, each finding with the severity its check declares: *blocking*,
*warning* or *observation*. An agent reports every finding, none summarised away,
and says which of its own findings the check did not produce.

**The verdict is scoped.** READY states what the agent can reason on, and on what
it cannot: *READY* with its scope, or *NOT READY* with what blocks it. A verdict
that names no scope says nothing.

**The READY rule.** NOT READY means a blocking finding of the integrity check or
an acquisition state not reached (owner, 2026-11-18; § *Open points*).

**A Boot Report is evidence, not governed knowledge.** It is produced by a
reasoning assistant, and per `GOV-P-001` it creates no authoritative knowledge.
It is generated, disposable (`ENG-P-003`), and read by the human who decides.

---

## What implements it

| Part of the protocol | What implements it today |
|---|---|
| the Acquisition SPOT | the Context Bundle, exported by `scripts/export_project_sources.py` (`aistack.context_bundle`) |
| integrity warnings | the integrity checks, run by the Task `knowledge.integrity` (`aistack.integrity`) |
| acquisition, the report, the verdict | the agent itself, following this text; no program executes them |

The *Context Engine* of the August 2026 plan — a runtime that acquires, validates,
qualifies and builds the Operational Context — is **not built**. The protocol does
not need it to exist: it is what a first implementation of the protocol would
implement, and `ARCH-0010` states that the Knowledge, Context and Observation
services it would belong to are not built either.

---

## Open points

Decided by the owner on 2026-11-18, after the first agent run on the bundle of
`main` (`STD-0300` 2.1 to 2.3):

1. **The READY rule.** An agent's verdict is *NOT READY* when the integrity check
   reports at least one *blocking* finding (`aistack.cli.knowledge_integrity` exits
   non-zero), or when an acquisition state was not reached. Warnings and
   observations do not make a verdict NOT READY: they are reported, each one, and
   the verdict names the scope they limit. This is the reading of `STD-0300`
   criteria 2.5 and 2.6 that the owner kept.
2. **Where an agent finds this text.** The README carries one line that points to
   it (the README stays a presentation of the product: decision of 2026-11-17),
   and `FDN-0009`, which sent the reader to an *AI Boot* section of the README
   that `main` does not hold, now sends to this document.

Still left to the owner. None is decided here.

3. **The qualification of this artifact.** Its type, criticality (C3, as the other
   Foundation protocols) and confidence are proposed by the assistant that wrote
   it. Qualification is a human contribution (`FDN-0003` Article 4). It goes
   into the 2.1 release as a Draft.
4. **Cross-model verification.** Criterion 2.4 stays `not verified`; the owner
   decided on 2026-09-25 (`GOV-0002/OS-076`) that no further run is spent against
   the same two model families.
