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
| Raisonnements IA | `aistack.ai_runtime.reasoning_history` | `reports/generated/ai-reasoning/<subject>.json`, history at `reports/generated/ai-reasoning/history/<subject>/` — **corrected 2026-09-27, `GOV-0002/OS-082`**: this row previously read `reports/generated/history/ai-reasoning/`, implying it sits under the same top-level `history/` directory the other three streams do; measured directly against `reasoning_history.DEFAULT_OUTPUT_DIR`, it does not, and `project_observation_history`'s generic scan (`available_stems(generated_dir)`, § *Decision* 1's Open Points bullet) has therefore never actually found it |

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

**`pyoxigraph` is a core dependency of the `aistack` package itself**
(`pyproject.toml`, added same day as this ADR), not an extra a deployer
opts into. The owner's explicit requirement, 2026-09-27: the published
`bigbrother1969/aistack-core` image must be self-sufficient the moment
it is pulled from DockerHub — nobody who runs it separately installs the
graph engine, because `Dockerfile`'s `pip install .` already carries it,
the same way it already carries `PyYAML`. Pinned to `>=0.5.11`, the exact
version § *Context* confirmed on GIGABYTE, not a looser range nothing has
run.

**The container's volumes, resolved 2026-09-27.** `GraphStore` existing
was not enough on its own: nothing in the image actually called it
either, and declaring a volume for a path nothing reads or writes would
still have been the invented infrastructure `ARC-P-006` forbids —
closed instead by giving the graph its first real caller,
`aistack.cli.timemachine_rebuild` (`main()`, overriding `Dockerfile`'s
default `CMD` the same way `knowledge_integrity`'s own bundle argument
already does), before touching `docker-compose.yml` at all. One mount,
not two: `docker-compose.yml`'s `aistack-core` service binds
`./reports/generated:/app/reports/generated`, read-write — the graph
(`<generated_dir>/timemachine/graph`) lives inside the same tree the
four source streams already occupy and `FDN-0003`/`.gitignore` already
treat as one disposable area, so a second, separate mount for "just the
graph" would split one already-unified directory in two for no real
benefit. The FTS5 index (§ 12) has no such mount yet — it has no code
yet either, the Explications foundation's concern, not this patch's.

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
before it reaches the store: any fact whose subject is user data rather
than configuration or binaries (a Nextcloud or Immich file path, per R2's
own example) is dropped outright rather than masked — masking still
proves such a path exists and roughly where; dropping does not. This runs
inside the projection step itself, not as a property of the store or a
query-time restriction, so no path from a raw history file to the graph
skips it.

An earlier draft of this section attributed secret masking (API keys,
tokens, connection strings in AI prompts or commit messages) to
`aistack.observability`, a module that does not exist anywhere in this
codebase — `find`/`grep` across `src/` confirm it, and confirm no other
utility does this today either (`GOV-0002/OS-080`). Rather than invent a
detection scheme for a case the corpus has not yet shown, the owner's
decision, 2026-09-27: the filter ships with the user-data exclusion above
only. Secret-shape masking is deferred until a real instance turns up in
the 669 commits, the AI Runtime's `explain` corpus, or the imported
`claude/` notes — grounding the detector in an observed shape rather than
a guessed one (`ARC-P-006`).

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

### 13. The GUI is a fifth mini-app, read-only, LAN-only by the same convention as the other four

Decided with the owner, 2026-09-27, over a static-HTML page generated
once by a CLI command (`aistack.cli.console_render`'s own pattern,
already used for the console, Architecture and Health Cockpit): the
Time Machine is something a person chooses an instant or a subject in
and follows provenance edges from, not a fixed snapshot, so it belongs
with `priority_ui`/`selection_ui`/`network_discovery_ui`/
`troubleshooting_assistant_ui` — a separate FastAPI+Jinja2 process
(`timemachine_ui`, port 8186, "next free after the Troubleshooting
Assistant's 8185"), its own dedicated venv outside the governed one
(decision #9, 2026-08-29), its own `run_timemachine_ui.sh`/
`scripts/setup_timemachine_ui_env.sh` pair, linked from
`console_links.yml`.

**LAN-only is measured, not designed, here** — the other four mini-apps
already establish it as a pure operational convention, not a code-level
restriction: bound to `0.0.0.0` (reachable from anywhere on the LAN,
the owner's own laptop included), and kept off the public internet only
by never declaring an NPM Proxy Host for its port in Nginx Proxy
Manager, with `console_links.yml` linking to the direct LAN address,
never a `...persiaut-family.fr` subdomain. Roadmap R1 makes this a firm
rule for the Time Machine specifically, not the v1-only reduction the
other four still carry: it stays LAN-only until 1.7's connection layer
exists, regardless of how the others' own exposure evolves later.

**Read-only, never a writer.** `OxigraphGraphStore.read_only`
(`aistack.timemachine.oxigraph_store`, new alongside this decision)
wraps `pyoxigraph.Store.read_only`, measured 2026-09-27 not to conflict
with `aistack.cli.timemachine_rebuild`'s own read-write handle on the
same path — unlike a second `Store(path)`, which holds the same
exclusive lock a first one does. `timemachine_ui` opens a fresh handle
per request rather than one held for its process lifetime, so a rebuild
between two requests is picked up by the next one without a restart.
Reconstruction stays § *Decision* 10's own full rebuild, on demand, run
by the owner — never triggered by a screen a browser reaches.

**v1 scope, chosen with the owner over a raw SPARQL query box**: three
levels — the streams (`prov:Activity`), the instants each one recorded
(`prov:Entity` via `prov:wasGeneratedBy`, newest first), and every known
fact about one instant, generic or enriched (§ *Decision* 2's declared
predicates only — an outgoing fact this screen does not recognise falls
back to its own raw IRI rather than a guessed label). Implemented as one
generic node view rather than three separate routes: a `prov:Activity`
node's own incoming `wasGeneratedBy` edges *are* its instants list; any
node's outgoing facts are its own facts table; any node's other incoming
edges (an Agent's attributions, a causal request's own activity) are
"referenced by" — so following `prov:wasAttributedTo`/`prov:used` from
an entity to its Agent or its causal Request, and back, needs no special
case. `aistack.timemachine.iri` was split out of
`aistack.timemachine.projection` the same day, for the same reason
`aistack.history.format_instant`/`parse_instant` already is one shared
module for writer and reader: `timemachine_ui` needs `stream_stem` to
label a stream without duplicating `projection`'s own URN scheme,
though every IRI it ever *links* to comes straight out of a SPARQL
result, never reconstructed from parts.

**Mobile layout (R12)**, "bandes empilées" per the roadmap's own
wording — no earlier screen in this heritage declares a viewport meta
tag or a media query (measured 2026-09-27), so this is the first real
instance rather than an adaptation of one: every list — streams,
instants, facts, references — is a single column of stacked cards, and
each card's own label/value pairs stack too below 480px, so nothing
requires horizontal scrolling on a phone. This satisfies R12 for the v1
screens actually built here; the four richer validated maquettes (§
*Consequences*, below) will need their own mobile pass once 1.4/1.5
supply the data they assume.

### 14. Explications enter the graph: the first real source, `explain` answers

Decided with the owner, 2026-09-27: the Explications foundation (§ 7,
the persisted `KnowledgeArtifact` store, `aistack.explications`) had no
real caller until this patch. § 8 names four real sources; this one
imports the first — the AI Runtime's own `explain` answers, "already
collected... already kept since J7" — because they need zero new
collection code and already carry a real, clean per-subject shape
(`RuntimeFinding.subject`, e.g. `"booklore_db"`), unlike the other
three (669 commits with no clear graph subject; `pra_tests.yml`'s
~5 dated comments, a small but real corpus; `claude/` notes, whose own
scope — 5 files committed to this repository versus the 73 the owner's
Claude Project separately holds, unreachable by a rebuild running
headless on GIGABYTE — is an open question deferred to when that
source is actually imported, not decided speculatively here).

**`aistack.explications.from_ai_reasoning.import_explain_answers`**
walks every subject AI Reasoning History holds, keeps only the
`explain` operation of the three every finding already records
together (`reason`/`explain`/`recommend`), and records one `Proposed`
`KnowledgeArtifact` per answer not already imported —
`metadata["source_instant"]` (the source entry's own recorded instant)
is the idempotency key, read back from every version already recorded
for that subject rather than a second, separate ledger of what has
already run. **Building this importer is what found `GOV-0002/OS-082`**
(§ *Context*'s table, corrected above): AI Reasoning History's own real
layout does not match what `project_observation_history`'s generic scan
looks for, so it has never actually been reachable that way — this
importer gives it a real path into the graph regardless, through
Explications specifically, rather than widening the generic scan for
one stream's own layout quirk (new scope this patch does not need).

**`aistack.timemachine.projection.project_explications`** is a
separate function, not a branch inside `project_observation_history` —
an Explication's shape (`KnowledgeArtifact`, no `version`/`provenance`
pair at all, per that contract's own comment on the second, unwired
definition merged out of existence 2026-09-18) does not fit the
generic walk's envelope parser, and forcing it through would either
match nothing or bend that parser toward a second envelope shape it
was never about. It runs second in `aistack.cli.timemachine_rebuild`,
against the same store, never clearing it again — Explications is the
fifth source stream this ADR's own § *Decision* 1 already named ("soon
five"), added to the one rebuild pass, not a second graph. For each
Explication: it exists (`prov:Entity`), when it was recorded
(`prov:generatedAtTime`), what it explains (`aistack:explains`, a new
`subject_iri` construction — not `stream_iri`, since a finding's own
subject is not the same kind of thing as a collection stream and the
graph has no other node for most subjects yet), its `STD-0100`
confidence (a new `aistack:confidence` predicate) and, when recorded,
its workflow position (`aistack:explicationStatus`), and who or what
produced it (`prov:wasAttributedTo` an Agent from `artifact.source`,
the same `agent_iri` construction the four existing streams'
`provenance.origin` already uses).

**Two new CLIs, not one.** `aistack.cli.explications_import` (importing
raw sources into governed Explications) is deliberately separate from
`aistack.cli.timemachine_rebuild` (projecting whatever Explications
already holds): importing is the owner's own deliberate act — which
sources enter, at what confidence — not something every graph rebuild
should silently redo, the same "collect, then project" split every
other historicised stream already keeps between its own collector and
the Time Machine's read side. Running the importer twice without new
AI Reasoning History activity records nothing new the second time.

Verified in real execution against a real seeded `explain` answer
(`RuntimeFinding`/`AIRuntimeAnswer`/`record_ai_reasoning`, the exact
production types, no hand-typed JSON stand-in): import, then rebuild,
then a direct SPARQL query over the resulting store, confirming the
`aistack:explains`/`aistack:confidence`/`aistack:explicationStatus`/
`prov:wasAttributedTo` facts render exactly as designed.

## Consequences

- **`pyoxigraph>=0.5.11` is now a declared runtime dependency of the
  `aistack` package** (added 2026-09-27, still `Proposed`: like
  ADR-0010's own AI-language revision, this record did not need to wait
  for its own acceptance to be revised). Every environment that installs
  `aistack` — the venv on the laptop and on GIGABYTE, and every
  `bigbrother1969/aistack-core` image built from `Dockerfile` from now
  on — carries it, whether or not any Time Machine code has landed yet.
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
- **The projection is real, not only designed** (2026-09-27):
  `project_observation_history` reads `aistack.history` (`available_
  stems`/`available_instants`/`observation_at` — the same read side
  `aistack.cli.history_query` already exposes) rather than a second,
  parallel walk of `reports/generated/`, so the projection and the CLI
  a human already uses to inspect this history can never disagree
  about what a stream's history actually contains.
- **The GUI is real too, not only designed** (2026-09-27): `timemachine_ui`
  exists, runs, and was exercised end to end against a real seeded graph
  (two streams, one enriched by the `version`/`provenance` envelope, one
  not) — streams list, drill into instants, drill into facts, follow
  `wasAttributedTo`/`used` to an Agent/Request and back via "referenced
  by", both languages, the not-yet-built message when
  `aistack.cli.timemachine_rebuild` has never run. Its v1 scope is
  narrower than the four maquettes the roadmap already validated for the
  Time Machine — § *Open Points* states the gap explicitly rather than
  leaving it to be discovered later.
- **Explications is real too, not only founded** (2026-09-27, § 14):
  `aistack.explications.from_ai_reasoning.import_explain_answers` and
  `aistack.timemachine.projection.project_explications` exist, are
  wired into `aistack.cli.timemachine_rebuild` as the fifth stream, and
  were exercised end to end against a real seeded `explain` answer —
  import, rebuild, and a direct SPARQL query over the result. Building
  this importer is what found `GOV-0002/OS-082`, resolved the same day
  by giving Raisonnements IA a real path into the graph through
  Explications rather than reshaping the generic scan. The three other
  named sources (§ 8) remain not yet imported.

## Open Points

- ~~**The graph's public contract's exact shape**~~ — **resolved,
  2026-09-27**: `aistack.timemachine.graph.GraphStore` (`add`/`query`/
  `clear`), `aistack.timemachine.oxigraph_store.OxigraphGraphStore`,
  and the PROV-O/`aistack:` IRIs (`aistack.timemachine.vocabulary`) all
  exist. `aistack.timemachine.projection.project_observation_history`
  walks the four streams `available_stems(generated_dir)` actually
  finds and writes what each one honestly states today: a generic
  entity/`prov:generatedAtTime`/`wasGeneratedBy` fact for every
  historical observation, of any stream, plus — where a stream's own
  content parses as the `version`/`provenance` envelope J3 already
  gave three of the four streams (Traces, Décisions CPU, Raisonnements
  IA) — `aistack:stableSubject` from `version.subject`,
  `prov:wasAttributedTo` an Agent from `provenance.origin`, and
  `prov:used` naming the request from `provenance.causality` where one
  exists. **Raisonnements IA carries the envelope but this generic
  walk never actually reaches it** (`GOV-0002/OS-082`, found
  2026-09-27): its own real, subject-keyed layout sits one level
  outside `available_stems`'s scan, so in practice only two of the
  four streams (Traces, Décisions CPU) are enriched by this walk —
  Raisonnements IA's real path into the graph is Explications (§ 14),
  through its `explain` answers specifically, not this generic scan.
  The twelve raw Observation History streams carry no envelope and get
  the generic facts only; parsing each one's own business schema (a
  Docker container's identity, a Beszel host's own name) for a richer
  mapping is real work still deferred to 1.5's collectors, not
  attempted here — inventing that mapping now, for streams no
  collector emits in that shape yet, would be exactly `ARC-P-006`'s
  forbidden guess.
- **How `aistack:occurredAt` is populated for the Kernel Runtime's own
  execution trace** — its events already happen and are recorded in the
  same call today, same as every other stream, so whether it ever
  acquires a real second timestamp depends on whether tracing is ever
  batched or replayed, which nothing currently does.
- **Compaction's exact mechanism and window** (§ 11) — reserved as a
  principle, not designed; a later version's concern once the corpus
  this ADR intentionally left small enough to rebuild in full actually
  stops being small.
- ~~**The GUI Time Machine itself**~~ — **resolved, 2026-09-27** (§
  *Decision* 13): a fifth mini-app, `timemachine_ui`, LAN-only the same
  operational way as the other four (R1), read-only against the graph
  this ADR defines via `OxigraphGraphStore.read_only`, with a
  responsive layout (R12). **Its v1 scope is narrower than the four
  maquettes the roadmap already validated** (a time ribbon, a network
  tree, a "why" panel) — those assume `aistack:occurredAt`, collection
  gaps and Explications, none of which this graph holds yet (1.4/1.5's
  own concern); building toward their visual richness ahead of that
  data would be exactly the invented infrastructure `ARC-P-006`
  forbids. What shipped instead reproduces `aistack.cli.history_query`
  from the graph — streams, the instants each recorded, the facts known
  about one instant, and the reverse edges (agent, causal request) the
  enriched three-of-four streams already carry — so the graph is seen
  to agree with the files it was built from before anything richer is
  built on top of it. Named here so the gap between what was demoed and
  what shipped is stated, not silently left for whoever opens the four
  maquettes next to discover on their own.
- ~~**The container's volumes for the graph's data**~~ — **resolved,
  2026-09-27** (§ 1's addendum): `aistack.cli.timemachine_rebuild`
  gives the graph its first real caller, and `docker-compose.yml`'s
  `aistack-core` service binds one read-write volume,
  `./reports/generated:/app/reports/generated`, covering both the four
  source streams and the graph's own on-disk files
  (`<generated_dir>/timemachine/graph`) in the one already-disposable
  tree they share. The FTS5 index still has no mount — it still has no
  code, the Explications foundation's concern.
- **Secret-shape masking in the projection filter** (§ 6) is deliberately
  not built yet — the owner's decision, 2026-09-27, once § 6's earlier
  attribution to a nonexistent `aistack.observability` was found and
  corrected (`GOV-0002/OS-080`): ship the user-data exclusion only, and
  design a real detector once an actual instance of a secret shape turns
  up in the imported corpus, rather than guess at the vocabulary of
  secrets no one has observed here yet.
