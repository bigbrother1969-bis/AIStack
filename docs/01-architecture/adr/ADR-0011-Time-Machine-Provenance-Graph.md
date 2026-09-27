---
artifact:
  id: ADR-0011
  title: Time Machine Provenance Graph
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Proposed
  owner: Architecture
  created: 2026-09-27
  updated: 2026-09-27

relations:
  references:
    - FDN-0003
    - STD-0100
    - ADR-0004
    - ADR-0008
    - ADR-0009
    - ADR-0010
    - GOV-0002
---

# ADR-0011 — Time Machine Provenance Graph

## Status

Proposed, 2026-09-27.

Written the day the owner took the decisions it records, left `Proposed`
rather than accepted the same day — the rule adopted 2026-08-21 (ADR-0010
§ Status carries the same note).

## Context

*Measured on 2026-09-27, at commit `f78d1c3`.*

`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` opens the road from 1.2 to 2.0
and assigns 1.3 the Time Machine's graph, its GUI, and the pourquoi in
read form. Its own § *Point de départ* names what already exists; this
section restates only what direct measurement of the repository adds to
or corrects in that account.

**Four historicised streams exist today, not five.** Each writes through
`aistack.generators.history.write_artifact_with_history`, which keeps a
stable path (`latest_path`) and, beside it, an indefinitely-retained,
timestamped copy under `history/<stem>/`:

| Stream | Writer | Path |
|---|---|---|
| Observations | `DockerObservationArtifactGenerator` and eleven sibling provider generators (`compose`, `docker`, `http_probe`, `beszel`, `network_docker`, `jellyfin`, `syncthing`, `filesystem`, plus the three renderers) | `reports/generated/history/<stem>/` |
| Traces | `aistack.kernel.tracing.repository.file` | `reports/generated/history/execution-trace/` |
| Décisions CPU | `aistack.priority.decision_history` | `reports/generated/history/resource-priority-decision/` |
| Raisonnements IA | `aistack.ai_runtime.reasoning_history` | `reports/generated/history/ai-reasoning/` |

Explications is not a fifth stream that exists today — it is what this
ADR's own § *Decision* 7 adds, the "cinq historiques + explications" the
roadmap's § 1.3 names as the projection's eventual input.

**Every one of the four lives entirely under `reports/generated/`, and
that whole tree is gitignored** (`.gitignore` line 46, no exception for
`history/`). The roadmap's own § *Point de départ* states "patrimoine
dans git" for this workstream; measured directly, that is not so — not
one byte of any of the four streams is source-controlled. `reports/
generated/` being disposable is deliberate and correct for the artifacts
it was designed to hold (`ENG-P-003`, generated pages rebuilt on demand);
historicised streams are a second, later tenant of that same disposable
directory, and nothing distinguishes them from the pages around them to
whatever backs up the host. This sharpens rather than merely repeats R4:
the Time Machine's own history is not "in an unverified backup" — as
found, it is in **no** backup at all, verified or not, and no version
control either. § *Decision* 11 and the roadmap's own 1.3 item 7 (AIStack
in its own PRA) are the response.

**`TemporalEvent` (`aistack.kernel.time.event`) carries no timestamp of
its own**, by design: its docstring states the instant a stream records
is the one the history filename already encodes, and a second,
independent timestamp on the event would be one more fact free to drift
from it. That filename time is *recording* time — when
`write_artifact_with_history` ran — never *occurrence* time — when
whatever the event describes actually happened on the system it
describes. The two coincide today because every writer observes and
records in the same call, but nothing enforces that they must, and a
batched or replayed collector (1.5's `docker events`, arriving after the
fact for something that happened earlier) would make them differ for
real. This is R3's bitemporal requirement restated against the actual
type that will need the second field.

**`Provenance` (`aistack.kernel.time.provenance`) carries no links to
other events**, only two strings: `origin` (which component produced the
snapshot) and `causality` (the request or task that caused it,
optional). Nothing here is a graph edge — a reader holding one
`Provenance` cannot walk to the event it names, only read a string that
happens to match its identifier if it looks it up itself. This is the
roadmap's own "provenance sans liens", confirmed by reading the contract
rather than assumed from its name.

**`STD-0100`'s `confidence` scale has exactly three levels** — `Verified`
· `Reviewed` · `Declared` — and all three describe a human's relationship
to a claim: it was checked against execution, or read and accepted by a
second person, or stated by its own author. None fits an AI-authored
explanation nobody has yet read, which is neither an execution check nor
a stated human belief. This is the gap the roadmap's 1.3 item 4 names as
"amendement de `STD-0100` (niveau proposé)".

**`pyoxigraph` runs on GIGABYTE's real CPU, confirmed 2026-09-27.**
GIGABYTE's Phenom X4 predates AVX2 — the same absence that made
`OPENBLAS_CORETYPE=NEHALEM` necessary for `numpy`/`scikit-learn` and made
Transmute unusable outright. Unlike those, `pyoxigraph` 0.5.11 installed
and ran a trivial `Store` round-trip (`Quad` inserted, one row read back)
on GIGABYTE itself before this ADR was written, per `GOV-P-001` (a real
fact confirmed on the owner's own hardware before it is built on, not
assumed from the library's own claims or from a different machine).

## Decision

### 1. Oxigraph is the engine; the files stay the truth

`pyoxigraph`, embedded (no separate server process, no new port, no new
service to declare in `pra_tests.yml` beyond the graph's own snapshot —
§ 11), confirmed to run on the reference host. The graph is built from
the four existing historicised streams plus Explications (§ 7); nothing
is ever written to the graph that was not first written to one of those
files. `FDN-0003`'s "generated artifacts are disposable" already
governs `reports/generated/`; this ADR extends the same rule to the
graph rather than creating a second regime for it — the graph is deleted
and rebuilt exactly like any other generated artifact, and § *Decision*
10 states when that happens.

A thin contract sits between the projection and the store —
`aistack.timemachine.graph.GraphStore` (`add`, `query`, `clear`) — so a
future engine swap (R9 of ADR-0009's own kind of caution, not yet a real
need) touches one adapter, not every caller. `pyoxigraph` is the only
implementation; the contract is not speculative plumbing for engines
nobody has chosen (`ARC-P-006`), it is the same "neutral interface in
front of one real implementation" `ADR-0005`'s Context Bundle Engine
already established for a comparable reason.

### 2. PROV-O plus four AIStack extensions

Every fact the graph carries is a `prov:Entity`, `prov:Activity` or
`prov:Agent`, related by the standard PROV-O predicates the roadmap's own
table already enumerates (`prov:wasGeneratedBy`, `prov:used`,
`prov:wasDerivedFrom`, `prov:wasRevisionOf`, `prov:wasAssociatedWith`,
`prov:wasAttributedTo`, `prov:generatedAtTime`, `prov:invalidatedAtTime`).
Four predicates outside that vocabulary are declared under an
`aistack:` namespace, because PROV-O has no native way to state them:

- `aistack:partOf` — the structural containment a network, host, stack
  and container form (`aistack:Network aistack:partOf` nothing;
  `aistack:Host aistack:partOf aistack:Network`; and so on down to the
  container) — orthogonal to provenance, needed for the tree the GUI
  walks (roadmap item 4, arriving in full in 1.4).
- `aistack:explains` — an Explication's `prov:Entity` to the subject it
  explains; not `prov:wasDerivedFrom`, which already means something
  else (an AI explanation *is* derived from its context, via the
  standard predicate — it separately *explains* its subject, via this
  one).
- `aistack:stableSubject` — see § 3.
- `aistack:collectionGap` — see § *Decision* 9.

### 3. Identity is a declared string, never a Docker id

A subject the graph tracks across time — the thing an upgrade recreates,
the thing a Compose stack redeploys — is named by
`aistack:stableSubject`: the Compose project and service name when one
exists (`compose_project/service`), or an explicitly declared name for
anything Compose does not cover. A container's own Docker id is recorded
as an attribute of one state, never as the identity the fil des états
threads through, because recreation always changes it and identity by
definition must not. This is R3's first half, and it is a modelling rule
this ADR fixes now, before 1.5's collectors have anything to disagree
about — a rule adopted after collection exists is a migration; adopted
before, it is just how the field was always populated.

### 4. Bitemporal: occurrence time and recording time, both kept

Every fact carries `prov:generatedAtTime` for *recording* time — read,
today, from the same history filename `TemporalEvent`'s own docstring
already names as authoritative, so nothing already written needs
correcting. Where a collector can state *occurrence* time
independently — Docker's own event timestamp, once 1.5's collectors
exist — it is stored as a second, explicit `aistack:occurredAt`. Where it
cannot (today, every writer, since observation and recording happen in
the same call), `aistack:occurredAt` is left unstated rather than copied
from `generatedAtTime` — an absent second fact is honest; a duplicated
one would read as two independent confirmations of a single guess.

### 5. Clock source and drift are declared facts, not assumptions

Every host that contributes facts declares which clock backs its
timestamps (`aistack:clockSource`, e.g. `"GIGABYTE:systemd-timesyncd"`);
comparing `occurredAt` across two hosts without a drift measurement
between their clocks would state an ordering the data cannot support.
Measuring and recording that drift is 1.5's concern (its collectors are
what runs on more than one host); this ADR only reserves the field so
1.5 has somewhere governed to write it rather than inventing the shape
under deadline.

### 6. The projection filters before anything is indexed

A pass — `aistack.timemachine.projection.filter` — runs on every fact
before it reaches the store: secrets (the shapes `aistack.observability`
already knows to redact, extended here to AI prompts and commit
messages) are masked, and any fact whose subject is user data rather
than configuration or binaries (a Nextcloud or Immich file path, per R2's
own example) is dropped outright rather than masked — masking still
proves such a path exists and roughly where; dropping does not. This runs
inside the projection step itself, not as a property of the store or a
query-time restriction, so no path from a raw history file to the graph
skips it.

### 7. Explications are `KnowledgeArtifact`, not a new contract

Reusing `aistack.contracts.artifact.KnowledgeArtifact` exactly, per the
roadmap's own choice: `id` names the subject explained, `source` names
the author (a human's identifier once 1.7 exists, a model name and
version, a rules generator's name, or `"commit:<sha>"` for an imported
message), and a new `confidence` value, `Proposed`, is added to
`STD-0100`'s scale (§ *Context*'s gap) — sitting below `Declared` in the
ordering the standard already documents, since an unread AI draft claims
less than its own stated author's belief. Two further states an
Explication can reach are not confidence levels: `Validated` (a human
becomes a second, confirming author — `prov:wasAttributedTo` gains a
second edge) and `Discarded` (kept, never deleted, R6) — both recorded
as `aistack:explicationStatus`, distinct from `confidence` because
`STD-0100`'s scale describes epistemic strength and this describes a
workflow position; collapsing them would make a `Discarded` entry read as
a confidence level nothing else in the standard has.

A correction is a new `KnowledgeArtifact` version linked to its
predecessor by `prov:wasRevisionOf`; nothing already written is edited or
removed.

### 8. Import target: commits, `pra_tests.yml`, existing `explain`s, and `claude/` notes

The 669 commit messages, the dated comments already in `pra_tests.yml`,
and the AI Runtime's own `explain` answers (already kept since J7) enter
as `Proposed` — none of them a human's own stated claim; a commit
message states what its author did, not that they vouch for it as an
explanation. The owner's decision, 2026-09-27: the project's own
`claude/*.md` session notes are imported too, at the same `Proposed`
level — never higher, since `STD-0100` (independently of this ADR) is
explicit that a `claude/` citation is provenance, never the sole
statement of a fact or a decision. Importing them as `Proposed`
Explications keeps that rule intact: a `Proposed` Explication is exactly
provenance, not a validated claim, and stays that way until a human
reads and validates one — at which point it is that human's validation,
not the note, that the graph credits.

### 9. Collection gaps are their own fact

When a stream that has produced facts before stops — a collector
crashes, a host is unreachable — the *absence* is recorded as
`aistack:collectionGap` (a subject, a stream, a start, and, once it
resumes, an end), not inferred at query time from a longer-than-usual gap
between two facts. Recording it explicitly rather than inferring it means
the chronology can display "no observation between X and Y" as a stated
fact rather than a silence that looks the same as a quiet period (R11).
1.3 declares the model; 1.5's collectors are what actually detects a stop
and writes the fact.

### 10. Full rebuild on demand, never incremental, never scheduled

The owner's decision, 2026-09-27: rebuilding the graph means deleting it
and replaying every filtered fact from the four (soon five) source
streams, on demand — no cron, no partial update reconciling drift between
graph and files. This is the simplest implementation of "projection,
reconstructible" already decided for the graph's status, and it is
sufficient while the corpus is what § *Context* measured (74 knowledge
artifacts, four historicised streams still small enough that a full
`history_query`-equivalent walk completes quickly) — a real number the
owner can watch stop being small, rather than a guess about when
incremental update would start paying for itself.

### 11. Retention, budget, and AIStack's own PRA coverage

No fact already written is ever deleted by rotation; a **compaction**
pass (a later version's concern to implement, reserved here as a
principle) may summarize facts older than a declared window without
destroying the files that back them — "never overwritten" survives
compaction because compaction operates on the graph's contents, never on
the four source streams. A disk budget is declared per host before this
graph, or any future historicised stream, is allowed to grow unbounded;
GIGABYTE's own disk-cleanup history (`/areas/homelab.md`) is precedent
for what an unbudgeted growth eventually costs. Per § *Context*'s
correction, `reports/generated/` — the graph's own source data — carries
no backup today; the roadmap's own item 7 (service `aistack` declared in
`pra_tests.yml`, `reports/generated/` and Explications covered by a real
backup, a real restoration test run by the owner) is this ADR's
condition for calling any of the above safe to rely on, not an optional
extra alongside it.

### 12. SQLite FTS5 for full-text search over Explications

The owner's decision, 2026-09-27: `sqlite3` (stdlib) with an FTS5 virtual
table indexes Explication text, separately from Oxigraph — Oxigraph
answers SPARQL graph questions, FTS5 answers "which Explications mention
Vikunja"; neither engine is asked to do the other's job. The FTS5 index
is rebuilt on the same trigger as the graph (§ 10) and is exactly as
disposable — a `.sqlite` file under `reports/generated/`, covered by the
same PRA gap § 11 names and the same eventual fix.

## Consequences

- Nothing already committed to any of the four streams needs migrating;
  every fact this ADR describes is derived from what they already
  contain, at read time, by the projection (§ 6) — no schema owns
  writing to them changes.
- A new writer joining any of the five streams (a 1.5 collector, a 1.7
  user action) must state `aistack:stableSubject` and, where it can,
  `aistack:occurredAt` and `aistack:clockSource` from the day it is
  written — retrofitting identity or bitemporal facts onto a writer that
  shipped without them is real, avoidable work this ADR is meant to
  prevent.
- `STD-0100`'s confidence scale gains a fourth value (`Proposed`) sitting
  below `Declared`; every existing artifact's own `confidence` field is
  unaffected — the new value is additive, not a redefinition of the
  other three.
- Until § 11's PRA condition is met, the graph, its FTS5 index, and the
  four streams that feed it are all, honestly, unprotected data on one
  host's disk — this ADR does not claim otherwise while that gap is
  open.

## Open Points

- **The graph's public contract's exact shape** (`GraphStore`'s method
  signatures, the RDF vocabulary's exact IRIs) is left to the
  implementing patch rather than fixed here; this ADR fixes the model,
  not the Python interface.
- **How `aistack:occurredAt` is populated for the Kernel Runtime's own
  execution trace** — its events already happen and are recorded in the
  same call today, same as every other stream, so whether it ever
  acquires a real second timestamp depends on whether tracing is ever
  batched or replayed, which nothing currently does.
- **Compaction's exact mechanism and window** (§ 11) — reserved as a
  principle, not designed; a later version's concern once the corpus
  this ADR intentionally left small enough to rebuild in full actually
  stops being small.
- **The GUI Time Machine itself** (roadmap item 6, R1's LAN restriction,
  R12's mobile layout) is this ADR's consumer, not its subject — it
  reads the graph this ADR defines, and is designed separately.
