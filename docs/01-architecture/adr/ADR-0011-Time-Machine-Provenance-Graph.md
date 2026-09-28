---
artifact:
  id: ADR-0011
  title: Time Machine Provenance Graph
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.5
  status: Proposed
  owner: Architecture
  created: 2026-09-27
  updated: 2026-09-28

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

The commit messages (669 at the time this ADR was first written; 695 by
the time the last of the four sources was actually imported, § 17 —
growing history, not a stale count corrected in place), the dated
comments already in `pra_tests.yml`, and the AI Runtime's own `explain`
answers (already kept since J7) enter as `Proposed` — none of them a
human's own stated claim; a commit message states what its author did,
not that they vouch for it as an explanation. The owner's decision,
2026-09-27: the project's own `claude/*.md` session notes are imported
too, at the same `Proposed` level — never higher, since `STD-0100`
(independently of this ADR) is explicit that a `claude/` citation is
provenance, never the sole statement of a fact or a decision. Importing
them as `Proposed` Explications keeps that rule intact: a `Proposed`
Explication is exactly provenance, not a validated claim, and stays
that way until a human reads and validates one — at which point it is
that human's validation, not the note, that the graph credits.

**Corpus scope for `claude/` notes, decided the same day this source's
own import was scheduled (2026-09-27, deferred from here until then):**
only the 5 files this repository itself versions under `claude/*.md`,
not the 73 documents the owner's Claude Project separately holds on
claude.ai. `aistack.cli.timemachine_rebuild` runs headless on GIGABYTE,
reading only this repository's own tree — it has no path to the
Project's documents without a new export mechanism this ADR does not
build; widening the corpus to reach them is its own future decision,
not a default this one silently assumes.

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

**Built, 2026-09-28, before § 20's own remaining three collectors —
the owner's own decision.** `aistack.generators.collection_gap
.record_collection_gap` is the one shared mechanism every 1.5 monitor
calls at its own startup, not one implementation per collector: a
monitor cannot write anything while it is not running, so the only
moment it can ever detect a gap is the moment it comes back up, with
both ends already known — its own last checkpoint (where coverage
last reached) and "now" (where it resumes). This is why a
collection-gap fact is always written whole, start and end together,
never as an "open" interval a still-down collector could not have
written anyway — exactly this section's own "once it resumes, an end"
already said, just not yet built when it was written. A first run ever
(no checkpoint) writes nothing — there is no prior coverage to have
gapped from, the same restraint `docker_events_monitor`'s own
`FIRST_RUN_LOOKBACK_SECONDS` already holds for `since`. A dedicated
projector, `aistack.timemachine.projection.collection_gaps`, reads
every stream's own recorded gaps back and links each one to that
stream's own `prov:Activity` node (`aistack.timemachine.iri.stream_iri`
— never a second, competing activity minted for a stream this module
does not own) via `aistack:collectionGap`, its first real writer;
`aistack:occurredAt` states the gap's start, `prov:generatedAtTime`
its end (the recording instant, which — see above — is always the
resumption instant too). Retrofitted into `docker_events_monitor`,
1.5's one collector that already existed; the remaining three named
collectors call the same shared mechanism from the day each ships,
never retrofitted after the fact.

**First cut is stream-level, not per-tracked-subject.** § 9's own
wording names "a subject" for a gap; this first cut's subject is the
whole collector's own stream name (`"docker-events"`), not a narrower
subject such as one container this collector temporarily lost track
of while others kept reporting — the whole monitor process stopping
and resuming is the only kind of gap a checkpoint-based design can see
today. A future refinement, not invented ahead of a real case that
needs it (`ARC-P-006`).

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

### 15. Explications' second real source: `pra_tests.yml`'s own dated comments

Decided with the owner, 2026-09-27: of the three sources § 8 still
named unimported (669 commits, `pra_tests.yml`, `claude/` notes), this
one goes next — its whole corpus is a handful of hand-written prose
blocks that already name their own subject and date in plain text, the
least modelling to invent, unlike a commit's own unclear "subject" or
the `claude/` corpus's own scope question (resolved the same day:
**only the 5 files this repository actually versions**, not the 73 the
owner's Claude Project separately holds — a rebuild running headless
on GIGABYTE has no way to reach the latter without a new, separate
export mechanism this patch does not build).

`aistack.explications.from_pra_tests.import_pra_tests_comments` parses
the file's own bold-lede comment blocks (e.g. "**`arrstack` corrected
to `success`, same day (2026-09-26).**") — a block's subject is the
first backtick-quoted token in its lede; a block naming none this way
(one real block, "Vikunja gap closed...", names its subject only in
prose) is skipped and counted, not guessed at (`ARC-P-006`). No new
projection code was needed: `project_explications` already reads every
subject under `reports/generated/explications/` regardless of which
importer wrote it, so this source reaches the graph through the exact
same path § 14 built.

**A same-day correction is merged into one Explication, not recorded
as a second version.** `pra_tests.yml`'s own dates carry day
granularity only; recording `arrstack`'s "recorded as failed" and
"corrected to success, same day" as two separately-timestamped
versions would assert a precision the source does not have, and would
collide with a real defect this module's own design avoids rather than
triggers: two writes to one subject's history landing in the same
wall-clock second collapse to one queryable instant in
`aistack.history.query.available_instants` (its own docstring says
so), so the earlier of two same-second writes would silently stop
being visible to `read_explication_history` and to the graph
projection. Writing at most once per (subject, date) pair — same-day
blocks concatenated in file order — keeps the narrative arc readable
in one Explication and sidesteps the collision entirely, without
reaching into `write_artifact_with_history` to fix a timestamp
precision this source was never going to supply.

A new sibling CLI, `aistack.cli.explications_import_pra_tests` — the
first of `aistack.cli.explications_import`'s own "siblings, still to
come" its docstring already named — keeps importing this source the
owner's own deliberate act, same as the first.

Verified in real execution against the actual committed
`src/aistack/pra/definitions/pra_tests.yml` (not a fixture): 4 dated
blocks found, 1 skipped (Vikunja, no backtick subject), 2 subjects
recorded (`arrstack`, `raspberry`) — `arrstack`'s own two same-day
blocks correctly merged into one Explication with the failed-then-
corrected order preserved. Re-running the CLI recorded nothing new.
Rebuilding and querying the resulting graph directly by SPARQL
confirmed all 14 expected triples, including a single shared
`file:pra_tests.yml` Agent node attributed by both subjects'
Explications.

### 16. Explications' third real source: `claude/` session notes

`aistack.explications.from_claude_notes.import_claude_notes` imports
every `*.md` file directly under `claude/` — the 5 this repository
itself versions, per the corpus-scope decision § 8 now states. Each
note's subject and date are read from its own declared frontmatter
(`aistack.context_bundle.builders.frontmatter
.parse_artifact_frontmatter`, the same shared reader
`MarkdownArtifactBuilder` already uses for governed discovery, reused
directly — not that builder itself, an Explication being no more a
discovered document here than it was for `pra_tests.yml`) — `id` is
the subject, `updated` (falling back to `created`) is the date. A note
declaring neither this way falls back to its own filename's stem and
embedded date; one with neither is skipped and counted.

**Idempotency here is a content hash, not an instant or a date** —
unlike `explain` answers (a real recorded instant) or `pra_tests.yml`
(a stated day), a `claude/` note carries no marker of its own
separating "the fact" from "when it was noticed"; the file's text
changing *is* the correction event `ADR-0011` § 7 already models as a
new version. `metadata["source_content_hash"]` (sha256 of the raw
file) is what this importer compares before recording.

**Found while building this importer: `GOV-0002/OS-083`.** Measured
against all 5 real files, only 2 parse their frontmatter successfully.
One of the remaining 3 genuinely declares none — expected, and handled
by the documented fallback. The other 2
(`SESSION-2026-09-25-vs2-2.4-rerun.md`, `SESSION-2026-09-25-vs2-2.4.md`)
**do** declare a real `id`, but their own `status:` prose contains an
unquoted colon-space sequence that breaks `yaml.safe_load`, so
`parse_artifact_frontmatter` — which returns `{}` on any parse error,
by design — has silently never been able to read either one, for
anyone calling it, since the day each was written. Resolved by scope,
not by fixing the shared reader or the two files' own prose: this
importer's own fallback already imports both notes correctly, just
keyed by filename instead of the richer declared `id` — a real, stated
degradation, not a silent loss.

Verified in real execution against the actual 5 committed files: 0
skipped, 5 recorded (3 via the filename fallback per `OS-083`, 2 via
real frontmatter), a second run recording nothing new, and — proven
separately with a controlled clock, since same-wall-clock-second
writes to one subject collapse to one queryable instant — editing a
note's own content between two runs correctly records a second
Explication version rather than being lost to that collision.

**`OS-083` itself fixed at the source, 2026-09-28** — the owner asked
for the follow-up this section's own text named as optional. Both
files' `status:` prose is now quoted; `parse_artifact_frontmatter`
reads both correctly (confirmed directly). A future re-import of
these two notes records a new Explication under each one's real
declared `id`, alongside — not replacing — the Explication already
recorded under its old, filename-derived subject; that older entry is
not edited or removed (§ 7), it stands as an accurate record of what
the importer read before the correction.

### 17. Explications' fourth and last real source: commit history

Unlike the other three sources, a commit's own "subject" has no single
answer — measured, not assumed, against this repository's real 695
commits (669 when § 8 was first written): only 240 (35%) open with the
conventional `type(scope): message` first line that names a real
architectural subject in backtick-free plain text (`kernel`, `console`,
`explications`...); 149 (21%, overlapping) instead reference a
governance document id (`OS-071`, `ADR-0011`) with no scope at all;
318 (46%) have neither. Three shapes were put to the owner via
`AskUserQuestion` — scope-only with the rest skipped; scope falling
back to the referenced document id; or every commit, falling back to
its bare `type` as a coarse subject when nothing else names one — and
the narrowest was chosen: **only the 240 scoped commits are imported,
the scope is the subject, and a document id inside any message stays
in the Explication's own content, never promoted to a subject** — a
governance register entry and an architecture component are not the
same kind of thing, and a bare `type` like `docs` or `feat` is a
category, not an identity (`ARC-P-006`).
`aistack.explications.from_commits.import_commits` implements exactly
this: one `Proposed` Explication per scoped commit, the scope as
subject, the commit's own sha as its idempotency key (immutable and
already unique — no content hash or recorded instant needed, unlike
the other three sources), the commit's own author date as
`created_at`/`updated_at`, and `source` naming the commit itself
(`git:<sha>`) rather than its author — this repository's own commit
authors are not spelled consistently (`Fabrice`, `Fabrice Persiaut`,
`fabrice.persiaut`, `Claude`, `Claude Sonnet 5`, measured, not assumed),
and naming one of those spellings as the `prov:Agent` would fragment a
single real actor across several graph nodes; the real identity stays
readable in the Explication's own content (the full commit message),
just not promoted to `prov:wasAttributedTo`.

**A real write-pacing hazard, paced around rather than fixed at the
source.** `aistack.generators.history.write_artifact_with_history`
always stamps its history file with the real wall-clock instant of the
call, never a caller-supplied one, and `aistack.history.query
.available_instants` collapses two same-subject writes landing in the
same wall-clock second to one queryable instant (its own docstring
already says so plainly) — harmless for the other three sources' small,
naturally-spaced corpora, not harmless here: this repository's busiest
scope, `kernel`, has 38 real commits, all importable in one script run.
Measured: zero real commits share both a scope and an author-instant to
the same second, so the real history itself never collides — only an
unpaced batch import would manufacture a collision `git log` does not
have. Rather than add a caller-supplied-instant parameter to shared,
already-tested infrastructure five other producers also call, this
importer paces its own writes: before a second or later write to the
same subject within one run, it waits out the current wall-clock second.
Measured worst case, against the real 240-commit corpus across 80
distinct scopes: 160 forced one-second waits, under three minutes total
— a one-time cost for a one-time deliberate backfill, confirmed by the
real run (1m49s for the first import of all 240, 0.3s for an idempotent
second run finding nothing new).

Verified in real execution against this repository's own full history:
695 commits seen, 455 skipped (no conventional scope), 80 subjects, 240
Explications recorded; a second run recording nothing new; `kernel`'s
own history read back as all 38 distinct commits, in real chronological
order, none lost to the collision this section describes; a full
rebuild alongside the other three sources (87 subjects, 247
Explications, 1729 facts, none dropped) and a direct SPARQL query
confirming all 38 `kernel` Explications reached the graph, each
correctly ordered by its own real `generatedAtTime` and attributed to
its own distinct `git:<sha>` agent.

### 18. The network tree — `timemachine_ui`'s second view, from the live catalogs, never the graph

Roadmap `ROADMAP-1.2-TO-2.0-2026-09-27.md` § 1.4 assigns this version two
things: the "arbre hiérarchique pliable Réseau → Hôte → Stack →
Conteneur → Historique, avec recherche" (ungated), and a "file des
brouillons IA" (gated by R8). The owner's decision, 2026-09-28
(`AskUserQuestion`, "Arbre d'abord, R8 tranché plus tard"): build the
tree now; the R8/brouillons-IA gate is left open, for a later cadrage,
rather than resolved here by assumption. R8 itself requires closing
QUAL-0001's human evaluation before automatic drafts can ship; measured
directly against `claude/QUAL-0001-GOVERNED-LLM-EXPERIMENTS-HANDOVER.md`,
its 2026-09-25 closure addressed AI Runtime model choice in general (a
real production test on `deepseek-r1:1.5b` against the real
`OllamaEngine`), not the quality of an AI-generated Explication
specifically — a concept this repository did not have until 1.3's
Explications subsystem (§ 7, § 14-17 above) existed to generate one.
Stating that scope mismatch plainly, rather than silently treating
QUAL-0001 as already satisfying R8 or silently demanding a fresh
evaluation campaign nobody asked for, is what let the owner choose
instead of inheriting a choice.

Three further cadrage decisions, same day, one `AskUserQuestion` call,
all the "recommandé" option:

- **Emplacement: a new tab inside `timemachine_ui`, not a sixth
  mini-app.** The tree reads the same LAN-only FastAPI process, port
  8186, and — for Historique — the same `OxigraphGraphStore` § 13
  already gives it; a second process would duplicate both for no real
  gain. In the library analogy the roadmap itself uses, this is "Plan
  des rayonnages" placed right after "Salle de lecture" (§ 13's
  streams/instants/facts view), not a separate building.
- **Historique v1: the honest gap, not a richer promise.** Real
  per-container passive tracing is 1.5's own collectors' job (§
  *Open Points*, below, restates why); until then most nodes show
  "aucun historique lié pour l'instant" and only what already has a
  real `aistack:stableSubject` or `aistack:explains` match today (in
  practice, `jellyfin`'s CPU priority decisions) shows anything. Same
  discipline § 13's own v1-vs-four-maquettes gap already holds.
- **No Stack level for a remote host, ever.** A remote host (Raspberry
  Pi, Pi-hole VM) is known only through `network_docker_discover`'s
  own on-demand, never-automatic SSH `docker ps` scan — no compose
  file is ever read over SSH. Inventing a Stack grouping there from
  nothing observed would be exactly the guessed infrastructure
  `ARC-P-006` forbids; a remote host's containers attach directly to
  its host node.

**Where the hierarchy actually comes from — measured, not the graph.**
The local host's real Stack ⊃ Container structure is not itself in the
graph: the twelve raw Observation History streams carry no per-container
business schema yet (§ *Open Points*, above, already states this for
the generic projection walk), and inventing one now, for a shape no
collector emits, would be the same forbidden guess. It already exists
as real, live, governed data through
`DockerRuntimeCatalogBuilder`/`ComposeRuntimeCatalogBuilder`
(`src/aistack/catalog/docker/assets.py`,
`src/aistack/catalog/compose/builder.py`) — the same builders
`architecture_render.main` already calls to draw the Architecture view.
`ComposeRuntimeCatalogBuilder.build()` always sets a `"containers"`
metadata field per compose-project item, one entry per container the
project actually observed, regardless of whether that container has any
`depends_on` edge — confirmed by reading `compose/builder.py` directly,
and deliberately not reused from
`aistack.architecture.dependency_graph.build_dependency_graph`, which
narrows to "only projects with at least one edge" for its own, different
purpose (drawing dependency arrows, not enumerating membership). A
remote host's containers come the same way § *Decision* 9's own
`network_docker_discover` scan already writes them: the **last stored**
`network-docker-observation` snapshot, read via `aistack.history`
(`available_instants`/`observation_at`), never a live scan triggered by
this or any screen — the same "never triggered automatically" rule
`NetworkDockerDiscoveryProvider`'s own docstring already states and
`network_discovery_ui` already honours.

**`aistack.timemachine.tree`, built and verified 2026-09-28.**
`NetworkTreeNode` (id, label, kind, parent_id, depth, has_children) and
`RemoteHost` (host, containers) are plain dataclasses;
`build_network_tree` orders a caller-built `Catalog` pair into the flat,
depth-first, "every parent immediately before its own descendants" list
`aistack.catalog.views.media.tree.MediaTreeViewEngine` already
established for a surface that folds/renders in one pass without
knowing the tree's shape — followed here rather than a new
representation invented for this one screen. `parse_remote_hosts` reads
`NetworkDockerDiscoveryProvider.collect()`'s own real JSON shape,
tolerantly (a missing or malformed section degrades to "nothing
observed", never raises — the same reasoning
`build_dependency_graph` already gives for reading a governed artifact
that is machine-written, not hand-edited). `historique_names` answers
Historique from the graph, in exactly two batched SPARQL `SELECT`
queries built with `VALUES` (a `stableSubject` literal match, an
`aistack:explains` subject-IRI match via `aistack.timemachine.iri
.subject_iri`), never one query per candidate name — the same batching
discipline the Explications importers (§ 14-17) already hold for their
own idempotency checks. 11 unit tests (a real in-memory
`OxigraphGraphStore`, never a mock, for the `historique_names` cases;
plain `Catalog`/`CatalogItem` construction, no live provider mocking,
for the ordering cases), `ruff check`, and `mypy` are all clean.

**Not yet built, named here rather than implied finished**: the
`timemachine_ui` route, its template, the new i18n catalog entries, the
tree's own CSS, and the search itself — the same "state the gap
plainly" discipline § 13's own *Open Points* bullet already holds
between what was demoed and what shipped.

### 19. The provenance graph — `timemachine_ui`'s third view, one node centred on itself

Roadmap `ROADMAP-1.2-TO-2.0-2026-09-27.md` § 1.4's own "une vue du
graphe" is a separate line from § 18's tree, confirmed by re-reading
the roadmap directly rather than assuming the tree alone already
closed 1.4's ungated scope (`AskUserQuestion`, 2026-09-28, "Diagramme
visuel node-link (recommandé)" against two narrower alternatives — a
text list, or treating `node.html`'s existing text view as already
sufficient). A follow-up message the same turn — "on se cale sur les
maquettes que tu m'as proposé précédemment" — pointed this at a
specific one of the four already-validated maquettes: maquette 2,
"Suivre les évolutions," whose own wording is "graphe de provenance
centré sur l'étape." That phrase is this section's whole scope: one
node, and everything one hop away from it — not a whole-graph
explorer nobody validated, and not the ribbon or "pourquoi" panel the
other three maquettes separately ask for (§ *Open Points* already
states those remain outside v1).

**The same mechanism § 13's Architecture view already vendored, not a
second one invented.** `aistack.renderers.architecture
.dependency_mermaid.render_dependency_mermaid` already draws a real,
arrowed Mermaid `flowchart` from observed edges (`ARC-P-012`); the
vendored `mermaid.min.js` bundle `aistack.renderers.architecture.html
.load_vendored_mermaid_js` already ships is reused as-is. The new
module, `aistack.renderers.timemachine.provenance_mermaid`
(`ProvenanceNeighbor`, `render_provenance_mermaid`), turns `node`'s
own already-computed `facts`/`referenced_by` — the exact two lists §
13's text view already renders — into that same Mermaid text, rather
than a third graph-layout engine for one screen.

**One documented divergence from the Architecture precedent.**
`aistack.renderers.architecture.mermaid`'s own `_click_line` passes
`service.href` through `escape_text` before embedding it, correct
there because nothing about `escape_text` matters to an href that
never contains `&`. `ProvenanceNeighbor.href` is a self-built
`/node?iri=...&lang=...` query string that genuinely does — escaping
it would turn the real query separator into `&amp;`, corrupting the
link a click actually follows — so `render_provenance_mermaid` embeds
`href` verbatim, and the module's own docstring states why rather
than silently doing something different from its own precedent with
no explanation.

**Deliberately one hop, and never an activity's own instants.**
`node`'s existing route already excludes an activity's `wasGeneratedBy`
edges from `referenced_by` (shown instead as the chronological
`instants` list, § 13) — this section trusts and reuses that existing
exclusion rather than re-filtering, so a stream with many recorded
instants does not clutter a diagram that is supposed to be centred on
one étape. `_provenance_neighbors` (`timemachine_ui/app.py`) narrows
`facts`/`referenced_by` to real neighbours the same way `node.html`'s
own text view already distinguishes a link from a plain-text type
badge: an outgoing fact only becomes a neighbour when `object_iri is
not None and object_type_label_key is None`, the exact check the
template already made for `RDF_TYPE` — reused, not re-derived.
`aistack.timemachine.iri.short_label` generalises the existing
`stream_stem` across all six of that module's IRI prefixes, so any
neighbour — a stream, an observation, an agent, a request, an
Explication, a subject — gets a real label, defensively falling back
to the raw IRI on anything it does not recognise, the same discipline
`stream_stem` itself already holds.

**The vendored bundle's own `</script` hazard, checked again at this
new call site.** `render_html` (§ 13) already guards against the
vendored bundle ever containing a literal `</script` before embedding
it raw inside a `<script>` tag; `load_vendored_mermaid_js` itself
performs no such check — it is a bare file read, shared by both
callers. `timemachine_ui/app.py` repeats the same guard rather than
trusting `render_html`'s own check to somehow also cover a second,
independent embedding a few files away.

**Built, tested, and wired end to end, 2026-09-28**:
`provenance_mermaid.py` (8 unit tests: the centre alone, an outgoing
edge, an incoming edge, click-line placement and ordering, label
escaping, the href left deliberately unescaped, determinism);
`short_label` (2 more unit tests, alongside the existing `stream_stem`
suite); `timemachine_ui/app.py`'s `_node_href`/`_provenance_neighbors`
and the `node()` route's own wiring (`provenance_graph`, `mermaid_js`,
the repeated `_SCRIPT_TERMINATOR` check); `node.html`'s new "Graphe"
section (a "Graphe" heading always present, the diagram or the same
`.empty` convention every other section already holds), the vendored
JS and the Mermaid definition embedded via Jinja's own `tojson` filter
— Jinja2's built-in HTML-safe JSON escaping, the idiomatic equivalent
of `render_html`'s own manual `</`-replacement, confirmed by direct
inspection to encode a real `&` in an href as `&`, a JS string
escape a browser decodes back to the literal character at runtime,
never HTML-entity-corrupted; new `graph.*` i18n keys in both
catalogs; new `#provenance-graph`/`.render-error` CSS in `_style.html`.
Exercised end to end with a `TestClient` against a real, in-memory-then-
on-disk `OxigraphGraphStore` seeded with real PROV/`aistack:` triples
(never a mock) — both languages, a node with real outgoing and
incoming neighbours (`node0`/`node1`/`node2`/`node3` all present, click
hrefs intact through the `tojson` round-trip), and a node with none
(the `.empty` fallback, no diagram markup emitted at all) — plus the
full governed chain (`pytest`, `ruff check src tests timemachine_ui`,
`mypy src`).

### 20. Docker events — 1.5's first collector, a governed polling loop and its own dedicated projector

Roadmap `ROADMAP-1.2-TO-2.0-2026-09-27.md` § 1.5, "Traçabilité passive
des conteneurs, upgrades compris" — the version opened by the owner's
"go 1.5", 2026-09-28. Cadrage the same day, `AskUserQuestion`, resolved
two open architectural questions before any code: which of § 1.5's four
named collectors (`docker events`, periodic `docker diff`, package
inventory, digest drift) to build first — `docker events`, since it is
the source the upgrade events § 1.5 itself names (exec, pull, create,
recreate, destroy) come from, and every other collector's richer
"upgrade" correlation depends on having it; and how it should run — a
governed polling loop, the same shape `aistack.cli
.resource_priority_monitor` already established as this heritage's one
precedent for a long-running collector, over a continuous `docker
events` subscription this heritage has no precedent for at all (every
other provider's own `collect()` is a point-in-time snapshot; a
subscription would be the first process in this codebase attached to a
live stream rather than calling out and returning).

**The raw collector states nothing beyond what `ADR-0011` § 3-4 already
name as a collector's job.** `aistack.providers.docker.events` derives
exactly three facts from each real Docker event — `aistack
:stableSubject` (§ 3's identity rule: the Compose project/service name
when the event's own actor carries both, falling back to its plain
name, then its own Docker id only as a last resort), `aistack
:occurredAt` (§ 4's own still-unfulfilled field, first populated here
via Docker's own `timeNano`), and the action Docker recorded — and
keeps the raw payload alongside them, never replacing it
(`ARC-P-012`'s own boundary, "returns lines, never a verdict",
extended here to Docker events: correlating a `destroy`+`create` pair
into a richer "upgrade" fact is real interpretation, deliberately not
attempted by this collector — a later, separate concern, § *Open
Points*).

**A dedicated root, off the generic walk's own.**
`aistack.providers.docker.events_history` writes under `generated_dir
/ "docker-events"`, not `generated_dir` itself — the same reasoning §
7's Explications already established for keeping its own content off
`project_observation_history`'s `available_stems` scan: a Docker-events
batch (`since`/`until`, zero or more discrete events) does not fit the
generic two-tier fact model built for one subject's own snapshot, and
a dedicated projector, `aistack.timemachine.projection.docker_events
.project_docker_events`, is what actually understands it — the same
"a fifth mechanism where a fourth one does not actually fit" caution §
7's own docstring already names, applied here to a sixth. Wired into
`aistack.cli.timemachine_rebuild.main` as the third projection pass,
after Explications, against the same store, never clearing it again.

**Write-on-change, watermark checkpointing, one accepted edge.**
`aistack.cli.docker_events_monitor` polls every `POLL_SECONDS` (10s,
the agent's own proposed default — double `resource_priority_monitor`'s
5s, since nothing here watches for a human-perceptible transition —
the owner's to tune with a single edit, the same way that monitor's own
constant is already documented as theirs to tune); records a batch only
when it observed at least one new event (`aistack.priority
.decision_history.record_decision`'s own "write on change" cadence,
applied per-cycle here rather than per-priority-app); and persists its
own `since` watermark to a checkpoint file so a restart resumes from
where it left off rather than replaying or silently losing whatever
happened while it was down. The checkpoint advances to each cycle's
own `until`, not to the last event's own `occurred_at` — a quiet host
must still move the window forward — which accepts one stated,
undissolved edge: an event landing exactly on a previous cycle's
`until` boundary could in principle be seen twice, since Docker's own
`--since` is inclusive. Left as a known trade-off, not solved for a
duplicate this project has not yet observed in practice (`ARC-P-006`).
A first run with no checkpoint yet starts observing from the moment it
starts, never backfilling further back — an unbounded backfill against
a host's full Docker history is exactly the unmeasured scope
`ARC-P-006` warns against.

**Correction, found the same day on GIGABYTE, first real use.** "Starts
observing from the moment it starts" above meant `since = until = now`
on a first run — a zero-width window, not merely a cautious one: the
owner's very first `./run_docker_events_monitor.sh --once --dry-run`,
run exactly as `USAGE` itself prescribes ("for a first manual check
against the real Docker daemon"), printed nothing at all, and could
never have printed anything, whatever Docker had actually done —
`--dry-run` compounds it further, since it never persists a checkpoint
either, so a second manual check right after computes its own fresh
"now" and is exactly as empty as the first. `run_cycle`'s own default
is now `FIRST_RUN_LOOKBACK_SECONDS` (60s, a small bounded constant, not
the unbounded backfill the paragraph above still correctly warns
against) before `until`, applied uniformly to a first run whether
looping or `--once` — closing the gap between what this paragraph
described and what the tool's own `USAGE` text promised it could do.

**`aistack:clockSource` (§ 5) is still not populated.** This first
collector runs on GIGABYTE alone; § 5 reserves that field for once a
collector "runs on more than one host" and a drift measurement exists
between their clocks — § 1.5's own sequencing (GIGABYTE first, remote
hosts over SSH after) is exactly when that becomes real, not before.

**One new predicate.** `aistack:dockerAction` (`aistack.timemachine
.vocabulary`) — PROV-O has no predicate for which kind of occurrence
one Entity represents, and a container lifecycle stream is exactly a
sequence of these labels; named directly from Docker's own vocabulary
rather than a closed enum this project would have to keep in sync with
Docker's.

**Built, tested, and wired end to end, 2026-09-28**:
`aistack.providers.docker.events` (`collect_docker_events`,
`stable_subject_of`, `occurred_at_of`, `docker_action_of`, `enrich` —
14 unit tests, including the real Compose-label precedence, the
Docker-id-never-preferred rule, and a real nanosecond-precision
regression: `timeNano / 1_000_000_000` was measured to round the last
microsecond digit incorrectly on a real 19-digit value, fixed with
integer `divmod` instead); `aistack.providers.docker.events_history`
(`record_docker_events`, 3 tests); a seventh `aistack.timemachine.iri`
builder, `docker_event_iri` (keyed by batch instant and in-batch index,
since one cycle can record several events at once); `aistack.timemachine
.projection.docker_events` (`project_docker_events`, 6 tests, including
a direct assertion that the generic walk's own `available_stems` never
finds this stream); `aistack.cli.docker_events_monitor` (`parse`,
checkpoint load/save, `log_cycle`, `run_cycle` — 17 tests, real
subprocess boundary mocked, real tmp-path files, a first-run-bounded-
lookback regression, a dry-run-writes-nothing regression, a
`--once`-always-prints regression);
`deploy/systemd/aistack-docker-events-monitor.service` and
`run_docker_events_monitor.sh`, mirroring `aistack-resource-priority-
monitor.service`'s own install/watch instructions. Exercised end to
end via `aistack.cli.timemachine_rebuild` against a real recorded
batch (a real `subprocess.run` call never made — `docker` is not on
this verification host — but every step downstream of the raw event
payload run for real) — full governed chain
(`pytest`, `ruff check src tests timemachine_ui`, `mypy src`,
`knowledge_integrity`) clean. `timemachine_ui`'s own wiring — surfacing
`aistack:dockerAction`/`aistack:occurredAt` on a node's existing facts
view — is deliberately not part of this patch: § *Open Points* names
it as the next increment, once a real batch from GIGABYTE's own Docker
daemon has been observed at least once.

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
- **Explications' second source, `pra_tests.yml`, is real too**
  (2026-09-27, § 15): `aistack.explications.from_pra_tests
  .import_pra_tests_comments` and its own CLI,
  `aistack.cli.explications_import_pra_tests`, exist and were
  exercised end to end against the real, committed file — no new
  projection code needed, since `project_explications` already reads
  every subject Explications holds regardless of source. The `claude/`
  corpus-scope question § 8 left open is resolved: only this
  repository's own 5 files, not the owner's separate 73-document
  Claude Project. Two of four named sources (commits, `claude/` notes)
  remain not yet imported.
- **Explications' third source, `claude/` notes, is real too**
  (2026-09-27, § 16): `aistack.explications.from_claude_notes
  .import_claude_notes` and its own CLI,
  `aistack.cli.explications_import_claude_notes`, exist and were
  exercised end to end against all 5 real committed files. Building it
  found `GOV-0002/OS-083` — 2 of the 5 declare frontmatter
  `parse_artifact_frontmatter` has never actually been able to read,
  resolved by this importer's own filename fallback rather than by
  touching the shared reader or the two files' own prose.
- **All four named sources are now real** (2026-09-27, § 17):
  `aistack.explications.from_commits.import_commits` and its own CLI,
  `aistack.cli.explications_import_commits`, close the set — 240 of
  this repository's own 695 commits (the ones with a real conventional
  scope; the rest skipped and counted, not guessed at), each a
  `Proposed` Explication keyed by its own immutable sha. Building it
  surfaced no new defect, but did require actively pacing writes around
  the same `available_instants` same-second collision the other two
  real-source patches had each, separately, already designed safely
  around — this is the first of the four sources where that hazard was
  a real risk rather than a theoretical one, given how many commits
  this repository's busiest scopes already carry.
- **The network tree's `timemachine_ui` wiring is real too** (2026-09-28,
  § 18): a `/tree` route, its template, the new i18n entries and CSS
  exist and were exercised end to end (a `TestClient` against real
  rendered HTML, in both languages, with and without a search query,
  and with a seeded graph match) — `aistack.timemachine.tree` (§ 18's
  earlier patch) had no caller in `timemachine_ui` until this one.
  Native `<details>`/`<summary>` gives the fold/unfold the roadmap's
  own "arbre pliable" asks for with no JavaScript: every node open
  except a "stack" (containers hidden behind one click), a non-blank
  search forcing everything open since the filtered set already holds
  only matches and their ancestors. Historique links only the small
  set `historique_names` already confirmed has a real match
  (`historique_entity_iri`, never per candidate). R8/brouillons-IA
  remains its own open decision (§ 18's own text), untouched by this.
- **The provenance graph is real too, not only designed** (2026-09-28,
  § 19): `aistack.renderers.timemachine.provenance_mermaid`, `short_
  label`, and `timemachine_ui`'s own `/node` wiring exist and were
  exercised end to end (a `TestClient` against a real seeded graph, both
  languages, a node with real neighbours and one without). Maquette 2's
  "graphe de provenance centré sur l'étape" is the first of the
  roadmap's four already-validated maquettes to actually ship against
  this graph — § *Open Points*' existing "narrower than the four
  maquettes" gap narrows by exactly this much; the ribbon and the
  "pourquoi" panel remain outside v1.
- **1.5's first collector is real too, not only sequenced** (2026-09-28,
  § 20): `docker events`, cadrage-chosen as § 1.5's own opening
  collector, running as a governed polling loop
  (`aistack.cli.docker_events_monitor`), recording enriched, checkpointed
  batches (`aistack.providers.docker.events_history`) that a dedicated
  projector (`aistack.timemachine.projection.docker_events`) turns into
  graph facts — the first collector to populate `aistack:occurredAt`
  (§ 4) with a real, independently-stated instant rather than leave it
  unstated. `aistack:clockSource` (§ 5) and any correlated "upgrade"
  fact both remain open, by design — see § *Open Points*. Enabled as a
  real systemd service on GIGABYTE the same day, confirmed against real
  production traffic (18 real containers, hundreds of events per
  10-second poll) and, after a real rebuild, confirmed rendering
  correctly in `timemachine_ui` — see the *Open Points* entry this
  resolves.
- **R11, collection gaps, is real too, not only modelled** (2026-09-28,
  § 9's own addendum): `aistack.generators.collection_gap` (the shared
  detect-and-record mechanism every 1.5 monitor now calls at startup)
  and `aistack.timemachine.projection.collection_gaps` (its dedicated
  projector, `aistack:collectionGap`'s first real writer) exist,
  retrofitted into `docker_events_monitor`, and are wired into
  `aistack.cli.timemachine_rebuild` as a fourth projection pass. The
  owner's own decision, 2026-09-28: build this once, shared, before
  three more 1.5 monitors would each have needed it separately, rather
  than defer it the way `aistack:clockSource` and upgrade-correlation
  are deliberately still deferred above.

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
- ~~**The network tree's `timemachine_ui` wiring**~~ — **resolved,
  2026-09-28** (§ 18's own *Consequences* addendum): the `/tree` route,
  its template, the i18n entries, the CSS, and the search all exist and
  are verified.
- **R8 / the brouillons-IA gate** (§ 18) remains explicitly open — the
  owner's own 2026-09-28 decision was to build the ungated tree first
  and revisit R8 at a later cadrage, not to resolve it here by assuming
  QUAL-0001's 2026-09-25 closure (model choice, general) already covers
  Explication-quality evaluation specifically (a narrower question that
  did not exist as a concept before 1.3).
- **Multi-hop / whole-graph browsing** (§ 19) is deliberately not
  built — maquette 2's own wording is "centré sur l'étape," one hop,
  not a graph explorer nobody validated. A caller wanting to go
  further today follows a neighbour's own click-through, one node at a
  time; a second, deeper hop rendered in the same diagram is real
  future work, not assumed here.
- ~~**`timemachine_ui`'s own docker-events wiring**~~ — **resolved,
  2026-09-28, in production on GIGABYTE**: the monitor was enabled as
  a real systemd service, `timemachine_rebuild` run against 123 real
  batches (4764 events, 51148 facts written, 0 dropped), and the owner
  confirmed by screenshot that a node's existing generic facts view
  already renders every event with its real `aistack:stableSubject`
  and instant, no new template code required — exactly the "GUI
  construite au fur et à mesure" the owner asked for (2026-09-28),
  checked against the real Docker daemon this ADR's own text once
  named as unreachable from the verification host, not invented ahead
  of it.
- **Correlated "upgrade" facts** (§ 1.5's own wording: "Trace également
  les upgrades sur les containers docker") are not built by § 20's raw
  collector, deliberately — `ARC-P-012`'s boundary keeps a collector
  reporting what happened, never an interpretation of it. Recognising a
  `destroy`+`create` pair (or an image-digest change) as one upgrade,
  and attaching the before/after image and package-inventory facts §
  1.5 itself asks for, is real work for a later interpretation layer —
  informed by 1.5's remaining three named collectors (periodic `docker
  diff`, package inventory, digest drift), not guessed at ahead of them.
- **`aistack:clockSource`** (§ 5, reopened by § 20) stays unpopulated
  until § 1.5's own sequencing reaches a second host (GIGABYTE first,
  remote hosts over SSH after) and a real drift measurement exists
  between two clocks to record.
- **Parsing each of the twelve raw Observation History streams' own
  business schema** (reopened by § 20, originally named under "The
  graph's public contract's exact shape" above) is one collector
  narrower now that `docker events` has its own dedicated projector;
  the other eleven (a Beszel host's own name, a Compose catalog's own
  service list, ...) remain generic-baseline-only, each its own future
  decision rather than a pattern assumed to generalise from this one.
