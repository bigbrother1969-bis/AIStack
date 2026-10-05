---
artifact:
  id: ADR-0011
  title: Time Machine Provenance Graph
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.15
  status: Accepted
  owner: Architecture
  created: 2026-09-27
  updated: 2026-10-05

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

Accepted, 2026-10-05, by the owner — at the 1.9 cadrage, after the graph,
its four Docker collectors and its screens had run on GIGABYTE since 1.3.
What remains open is listed below and in § *Open Points*; accepting the
record does not close them.

Proposed, 2026-09-27.

Written the day the owner took the decisions it records, left `Proposed`
rather than accepted the same day — the rule adopted 2026-08-21 (ADR-0010
§ Status carries the same note).

## Implementation state

| Step | State |
|---|---|
| § 1 — Oxigraph, the files stay the truth | done — 1.3 (2026-09-27) |
| § 2 — PROV-O plus the AIStack extensions | done — 1.3 |
| § 3 — identity is a declared string (`aistack:stableSubject`) | done — 1.3, applied by the Docker collectors in 1.5 |
| § 4 — occurrence time and recording time | done for `docker-events` (`aistack:occurredAt`, 1.5); the other streams carry their recording time only, stated as such |
| § 5 — clock source and drift | not done — `aistack:clockSource` declared, never populated: one host, no second clock to measure against (§ *Open Points*) |
| § 6 — the projection filters before indexing | done for user-data roots (1.3); secret-shape masking not built, by the owner's decision (§ *Open Points*) |
| § 7 — Explications are `KnowledgeArtifact` | done — 1.3; since 2026-10-05 every version of a subject is read back, two written in the same second included (`aistack.history.every_version`) |
| § 8 — the four import sources | done — 1.3 (§§ 14–17) |
| § 9 — collection gaps | done — 1.5 |
| § 10 — full rebuild on demand | done — 1.3 (`aistack.cli.timemachine_rebuild`) |
| § 11 — retention, budget, AIStack's own PRA | not done — compaction and the disk budget are reserved; AIStack's own PRA coverage is part of 1.9 (decided by the owner, 2026-10-05) |
| § 12 — SQLite FTS5 over Explications | not done — the Explications view filters by text; no FTS5 index exists |
| § 13 — the GUI, read-only, LAN-only | done — 1.3 as a mini-app; superseded in its form by the single web application (`ADR-0012`, 2026-10-03), still LAN-only and signed-in (`ADR-0014`); the human acts of `ADR-0015` are its only writes |
| §§ 14–17 — Explications from `explain`, `pra_tests.yml`, `claude/` notes, commits | done — 1.3 |
| § 18 — the network tree | done — 1.4 (2026-09-28) |
| § 19 — the provenance graph, one hop | done — 1.4 |
| §§ 20–23 — the four Docker collectors | done — 1.5 (2026-09-28), 1.5.1 for the package inventory |
| § 24 — the ribbon, v1 | done — 1.5.1; replaced by § 26 |
| § 25 — the "upgrade" correlation | done — 1.5.1 |
| § 26 — ribbon v2 | done — 1.5.2 (2026-09-29/30) |
| § 27 — exec noise left out, packages once per image | done — 2026-10-02 |

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

### 21. `docker diff` périodique — 1.5's second collector, mount-filtered at the source, write-on-change per subject

Cadrage 2026-09-28 (`AskUserQuestion`, right after § 20 shipped),
grounded in live research before any code: `WebSearch`/`WebFetch`
against Docker's own reference
(<https://docs.docker.com/engine/reference/commandline/diff/>) and a
real `moby/moby` issue (#3840), not assumed from training data
(`ARC-P-006`, "search first"). Two facts that research settled,
directly: `docker diff`/`docker container diff` takes no `--format`
or JSON option at all — plain-text `<A|C|D> <path>` lines only, one
column, unlike `docker events`' own `--format {{json .}}` — and its
own exclusion of mounted-volume paths from that listing is not
reliable: a bind mount is indistinguishable from a real filesystem
change via `stat()` across storage drivers, a maintainer's own
clarification on that issue explains, and a real reported case shows
it misreporting a change inside a mounted volume.

Four decisions, all confirmed with the owner before any code: (1)
running containers only (`docker ps`, not `docker ps -a` — a stopped
container's filesystem is not drifting under active use); (2) volume/
mount paths filtered explicitly at the collector's own level, using
each container's own `docker inspect`-reported `.Mounts[].Destination`
— never trusted to `docker diff` itself (per the research above), and
never deferred to § 6's own projection-side `filter_fact` (a different
mechanism, built for a statically-declared root, not a per-container
mount Docker itself already states); (3) a shared identity module,
factored out *before* this collector rather than after — the owner's
own decision, the same "build the shared thing first" pattern already
set for R11 (§ 9's own addendum); (4) the full current diff listing
written on each write-on-change, never an invented incremental delta
— `docker diff` is already cumulative since container creation, not
since the last poll, so tracking a separate "since I last looked"
delta would only duplicate what Docker already does for free and risk
drifting from it.

**`aistack.providers.docker.identity`, the shared module decision 3
asks for.** `stable_subject_from_labels` is § 3's identity rule,
generalised off any source of Compose labels rather than cabled to
`docker events`' own `Actor.Attributes` shape — `aistack.providers
.docker.events.stable_subject_of` (§ 20) is now a thin adapter over
it, pulling `attributes`/`actor_id` out of an event's own `Actor`
before handing them to the shared rule; behaviour unchanged, a
refactor rather than a redesign, its own 14 tests still pass
unmodified. `list_running_container_names` (`docker ps`) and
`inspect_containers`/`identities_of` (`docker inspect`, every
container in one call, not one subprocess per name) round out the
module — `ContainerIdentity` pairs a container's own stable subject
with its declared mount destinations, the one shape both this
collector and the two still to come (dérive du digest, inventaire des
paquets) need from `docker inspect`.

**One subdirectory per subject, a real fork from § 20's own shape —
decided by what each stream's own "write on change" actually
compares.** A Docker event is individually new by nature (Docker
itself never reports one twice), so that stream only ever asks "is
there anything at all this cycle." A `docker diff` snapshot is
cumulative and, for a quiet container, often *identical* to the last
poll — the real question is "did the value change," which needs
something to compare against. `aistack.providers.docker.diff_history
.record_docker_diff` answers it by reading back the stable "latest"
file `aistack.generators.history.write_artifact_with_history` already
keeps per subject (`generated_dir / "docker-diff" / <subject> /
"docker-diff.json"` — a subject embedding a `/`, a Compose
`project/service` pair, simply nests one directory deeper; no
escaping, no second checkpoint state to keep in sync with it) —
the first stream in this package whose own novelty needs a read-back
rather than a value its caller already holds in hand
(`aistack.priority.decision_history.record_decision`'s own
`ApplyReport.changed` is computed by its caller, not read from disk).
`has_changed` is the read-only half of that same comparison, exposed
so `--dry-run` can report what would be recorded without writing
anything — the same distinction § 20's own monitor already draws.

**A dedicated projector that reverses the nesting.**
`aistack.timemachine.projection.docker_diff.project_docker_diff` finds
every subject root by locating each `history/docker-diff` leaf under
`generated_dir / "docker-diff"`, however deep a subject's own `/`
nests it — it cannot assume one `iterdir()` level per subject the way
`aistack.timemachine.projection.collection_gaps` safely can (that
module's own stream names never carry a `/`) — and rebuilds the exact
subject string from the path between the two. Wired into
`aistack.cli.timemachine_rebuild.main` as the fourth projection pass,
after docker-events, before collection gaps (which needs every
stream's own activity node to already exist).

**`aistack:changeCount`, not every changed path, as a graph fact.** A
snapshot can hold anywhere from zero to hundreds of paths; promoting
each to its own graph triple would turn a provenance graph meant to
answer "when did this happen, for which subject" into a bulk
file-change log nothing here queries that way. The full path list
stays exactly where it was recorded, reachable through
`aistack.cli.history_query` the same way any other stream's raw
content already is; `aistack:changeCount` (`aistack.timemachine
.vocabulary`, this heritage's first `xsd:integer`-typed literal —
every one before it was a plain string or `xsd:dateTime`) gives the
graph the one lightweight magnitude signal worth a fact of its own. No
`aistack:occurredAt` — `docker diff` states only that a path changed
*since the container's own creation*, never when.

**Built, tested, and wired end to end, 2026-09-28**:
`aistack.providers.docker.identity` (`stable_subject_from_labels`,
`list_running_container_names`, `inspect_containers`,
`identities_of` — 17 tests, including the container-vanished-between-
`docker ps`-and-`docker inspect` race); `aistack.providers.docker.diff`
(`collect_docker_diff`, `collect_running_container_diffs` — 13 tests,
including the real plain-text parsing shape and the mount-path
filter's own boundary discipline: a mount matches itself and its
children, never a sibling merely sharing its prefix); `aistack
.providers.docker.diff_history` (`record_docker_diff`, `has_changed` —
11 tests); a ninth `aistack.timemachine.iri` builder, `docker_diff_iri`
(keyed by subject and recording instant); one new `xsd:integer`
constant and `aistack:changeCount` in `aistack.timemachine.vocabulary`;
`aistack.timemachine.projection.docker_diff` (`project_docker_diff`,
10 tests, including a same-second-collision-aware regression for two
snapshots of one subject and a direct assertion the generic walk never
finds this stream either); `aistack.cli.docker_diff_monitor` (`parse`,
checkpoint load/save, `log_cycle`, `run_cycle` — 19 tests, real
subprocess boundary mocked, real tmp-path files, a checkpoint-still-
advances-on-a-quiet-cycle regression, a dry-run-writes-nothing
regression); `deploy/systemd/aistack-docker-diff-monitor.service` and
`run_docker_diff_monitor.sh`, mirroring § 20's own install/watch
instructions. Full governed chain (`pytest`, `ruff check src tests
timemachine_ui`, `mypy src`, `knowledge_integrity`) clean.
`timemachine_ui`'s own generic node-facts view (§ 19) already renders
this stream with no new template code, the same way § 20's own
*Open Points* entry found for `docker events`: `aistack:stableSubject`
already carries a friendly label there, shared across every stream
that states one, and `aistack:changeCount` degrades gracefully to its
raw predicate IRI (`_PREDICATE_LABELS.get(predicate, (None, False))`'s
own fallback) rather than failing to render — checked by reading that
view's own code, not yet re-confirmed against a real batch from
GIGABYTE's own Docker daemon the way § 20's entry was (`docker` is not
reachable from this verification host).

**Correction, found the same day on GIGABYTE, first real use** — the
same kind of gap § 20's own first-run-lookback correction closed for
`docker events`. Enabled as a real systemd service, the monitor's own
first `--dry-run` check reported all 59 running subjects as changed
(expected — a first observation ever, nothing to compare against);
once enabled for real, `timemachine_rebuild` against a few minutes of
real polling reported 163 snapshots for those same 59 subjects — far
more write-on-change activity than a few 10-second cycles should
plausibly produce. A diagnostic run directly against the real recorded
history (comparing each subject's first and most recent snapshot as
*sets* of `(kind, path)` rather than as ordered lists) found the cause:
`docker diff`'s own line order is not stable across repeated calls
against the same container, even when the underlying set of changes is
completely unchanged — 30 of the 32 multi-snapshot subjects held the
exact same set, merely re-ordered, on every poll (one, `firefly/
firefly`, was a real content change — new PHP session files an
actively-used container keeps creating). `aistack.providers.docker
.diff.collect_docker_diff` now sorts its parsed output by `path` (then
`kind`) before returning it, once, at the source — order was never
itself a fact worth keeping for this stream, unlike `docker events`'
own chronological order, which `aistack.providers.docker.events` never
touches — so `aistack.providers.docker.diff_history.has_changed`'s own
list-equality comparison, and the content actually written to history,
are both now deterministic for an unchanged real diff, without asking
every future caller of `collect_docker_diff` to remember to canonicalise
it themselves. 2 new regression tests (a reordered real transcript
parses identically; two calls returning the same set in different
order parse to the same list). Full governed chain re-run, clean.
GIGABYTE's own accumulated pre-fix history under `reports/generated/
docker-diff/` — real but low-value churn, `FDN-0003` disposable data,
never committed — is the owner's to clear before restarting the
service with the fix applied, not something this correction migrates
in place.

### 22. Dérive du digest — 1.5's third collector, a purely local comparison, no registry call

Cadrage decision 4 (§ 21, confirmed 2026-09-27 alongside the ordering
of all three remaining collectors, before any of them was built): a
running container's own current image digest, compared against the
last digest observed for the same `aistack:stableSubject` — the same
bitemporal, stable-identity machinery every other 1.5 collector
already uses, with no registry network call on either side. A changed
digest for a stable subject is § 1.5's own wording made concrete:
"l'image avant/après" for an upgrade is a real, local, observable
fact the moment `docker inspect` reports one, no external fetch
needed to say *that* something changed, only *what* it changed from
and to.

A fresh cadrage (`AskUserQuestion`) settled the two questions decision
4 left open, grounded in real research before any code
(`ARC-P-006`): which `docker inspect` field states this locally, and
how to capture it. `WebSearch`/`WebFetch` against a real incident
(GitHub, `pmdroid/barkvisor` #642) confirmed a container's own
`.Image` field is its current image's *configuration* digest
(`sha256:...`), a different kind of digest from an image's own
`RepoDigests` (a *manifest* digest, comparable only to what a registry
itself reports — Moby v27.5.1 itself does not reliably expose
`RepoDigests` on a container inspect at all, that issue's own findings
state). The two are not interchangeable, and confusing them is exactly
the false-positive trap that real tool's own bug describes — comparing
a container's configuration digest against a registry manifest digest.
This collector never makes that comparison: both sides of its own
"did it change" question are `.Image`, read by two successive
`docker inspect` calls on this project's own hosts, so the mismatch
does not arise.

**`ContainerIdentity` extended, not a second `docker inspect`
caller.** The owner's own decision: `aistack.providers.docker.identity`
already resolves every field `docker inspect` reports for a running
container in one call (§ 21's own shared-module decision, built
*before* this collector specifically so the two still to come would
not each need their own copy); `image_digest` is simply one more field
read off the same JSON entry `mount_destinations` already comes from,
default `""` for the (unobserved on this project's own hosts, but not
guaranteed by Docker's own contract) case where `.Image` is absent.

**`docker-digest`, not `image-digest`, for the stream/directory
name.** The owner's own decision: stays in the naming family § 20 and
§ 21 already established (`docker-events`, `docker-diff`) rather than
the roadmap's own French wording — this collector is specifically a
`docker inspect` fact, the same kind of thing its two siblings already
name themselves after.

**`aistack.providers.docker.digest`** (`collect_running_container
_digests`) mirrors § 21's own `collect_running_container_diffs` in
shape — running containers only (the same restriction, the same
reason: a stopped container's image reference is not drifting under
active use) — but skips, rather than records empty, an identity whose
own `image_digest` came back `""`: an empty digest is the absence of
an observation, not a real one, and `aistack.providers.docker
.digest_history`'s own write-on-change contract has nothing meaningful
to compare an empty value against.

**`aistack.providers.docker.digest_history`** (`record_image_digest`,
`has_changed`) is § 21's own write-on-change shape, one subdirectory
per subject, applied to a single string value instead of a list: the
same real question — "did the value change since last recorded" —
needing the same read-back against the stable "latest" file
`write_artifact_with_history` already keeps per subject
(`generated_dir / "docker-digest" / <subject> / "docker-digest.json"`).

**`aistack.timemachine.projection.docker_digest`**
(`project_docker_digest`) is a tenth `aistack.timemachine.iri` builder
(`docker_digest_iri`, keyed by subject and recording instant — the
same reasoning `docker_diff_iri` already holds) and a new predicate,
`aistack:imageDigest` (a plain string literal — an identifier, never a
magnitude, unlike `aistack:changeCount`), the one fact this stream
states beyond "it happened, for this subject, at this instant." No
`aistack:occurredAt`, the same restraint § 21 already documents for
the same reason: a digest observed this cycle states only that this
is the digest *now*, never when it last changed. Wired into
`aistack.cli.timemachine_rebuild.main` as the fifth projection pass,
after docker-diff, before collection gaps.

**`aistack.cli.docker_digest_monitor`** is § 21's own governed polling
loop (`POLL_SECONDS = 10.0`, unchanged — not tuned against a real
measurement, the owner's own decision to change with a single edit if
it ever needs to), R11 built in from its first version (never
retrofitted, the same rule every 1.5 monitor has held since § 20's own
addendum), `--once`/`--dry-run` for a first manual check against the
real Docker daemon before enabling as a service.

**Built, tested, and wired end to end, 2026-09-28**:
`aistack.providers.docker.identity` extended (`image_digest` on
`ContainerIdentity` — 2 new tests, the real digest capture and the
absent-field default); `aistack.providers.docker.digest`
(`collect_running_container_digests` — 4 tests, including the
empty-digest-is-skipped regression and two containers each getting
their own entry); `aistack.providers.docker.digest_history`
(`record_image_digest`, `has_changed` — 10 tests, the exact shape §
21's own `diff_history` suite already holds, against a single value
instead of a list); a tenth `aistack.timemachine.iri` builder,
`docker_digest_iri`; `AISTACK_IMAGE_DIGEST` in `aistack.timemachine
.vocabulary`; `aistack.timemachine.projection.docker_digest`
(`project_docker_digest`, 9 tests, including the same same-second-
collision-aware regression § 21's own projector suite already holds);
`aistack.cli.docker_digest_monitor` (`parse`, checkpoint load/save,
`log_cycle`, `run_cycle` — 20 tests, real subprocess boundary mocked,
real tmp-path files, the checkpoint-still-advances-on-a-quiet-cycle
and dry-run-writes-nothing regressions § 21's own monitor suite
already holds); `deploy/systemd/aistack-docker-digest-monitor.service`
and `run_docker_digest_monitor.sh`, mirroring § 20 and § 21's own
install/watch instructions. Full governed chain (`pytest`, `ruff check
src tests timemachine_ui`, `mypy src`, `knowledge_integrity`) clean in
clean-room, against a fresh GitHub clone.

`timemachine_ui`'s own generic node-facts view (§ 19) is expected to
render this stream with no new template code the same way § 20 and §
21's own entries already found for their streams (`aistack
:stableSubject` and `aistack:imageDigest` both degrade through the
same generic predicate-label mechanism) — not yet re-confirmed against
a real batch from GIGABYTE's own Docker daemon, the same open item §
21's own entry already carries forward for the same reason (`docker`
unreachable from this verification host).

With § 20, § 21, and this section, 1.5 now has three of its four named
collectors built, tested, and delivered — `docker events`, `docker
diff` périodique, dérive du digest. **Inventaire des paquets, the
fourth, is explicitly deferred past this release** — the owner's own
2026-09-28 decision (`GOV-P-001`): 1.5 ships with the three collectors
above, `docker exec`-based package inventory left for a later version
rather than assumed to block this one, per the roadmap's own § 1.5
sequencing (diff → digest → paquets) treated as an ordering, not a
bundling requirement.

### 23. Inventaire des paquets — 1.5's fourth and last named collector, shipped in 1.5.1

The owner's own 2026-09-28 decision, the same day: pick this deferred
collector back up for 1.5.1, alongside the first two `timemachine_ui`
pieces the roadmap's own four validated maquettes had left unassigned
to a version (§ *Open Points*, "The GUI Time Machine itself").

A fresh cadrage (`AskUserQuestion`) settled the two questions § 22's
own closing note left open, grounded in real research before any code
(`ARC-P-006`), confirmed with the owner:

**Mechanism: `docker exec` + `dpkg-query`, `/lib/apk/db/installed` as
the fallback, "no known package manager" when neither answers.**
Verified against `dpkg-query(1)`'s own manual page (man7.org): `-W`
with a custom `-f` format string (`'${Package}\t${Version}\n'`) prints
one package per line with no table-parsing needed — passed as a
single `subprocess.run` argv entry, never through a shell, so nothing
here needs to escape dpkg-query's own `${...}` placeholders. Alpine's
own `apk info -v` display output was considered and rejected: it
concatenates a package's name and version into one string with no
declared separator contract, an unreliable split — the structured,
documented alternative this collector uses instead is Alpine's own
`/lib/apk/db/installed` database (the Alpine wiki's own `Apk_spec`
page), a plain line-prefixed, blank-line-separated record format
(`P:` the name, `V:` the version). **Which mechanism actually
answered is itself recorded as a fact** (`"dpkg"` / `"apk"` /
`"none"`), never collapsed into an empty package list — a container
with no package manager this collector knows how to query is a
different observation from one a real inventory found genuinely
empty.

**`docker-packages`, staying in the naming family** — the owner's own
decision, the same reasoning § 22's own "`docker-digest`, not
`image-digest`" decision already gives: this collector's own
directory/stream name follows `docker-events`/`docker-diff`/
`docker-digest`, not the roadmap's own French wording ("inventaire des
paquets").

**`aistack.providers.docker.packages`**
(`collect_running_container_packages`, `collect_package_inventory`)
mirrors § 22's own `aistack.providers.docker.digest` in shape —
running containers only, the shared `aistack.providers.docker
.identity` module, unchanged — with `_dpkg_packages`/`_apk_packages`
each returning `None` (not `[]`) on failure, so "this mechanism did
not answer" and "a real, empty inventory" stay distinguishable
outcomes for `collect_package_inventory`'s own fallback chain.
`dpkg-query`'s own output is sorted by package name before being
returned, the same production-caution § 21's own `docker diff`
line-order incident already taught this project: no ordering
guarantee is documented for either mechanism's own output, so
canonicalising it here keeps the write-on-change comparison
deterministic without asking every future caller to remember to do it
themselves.

**`aistack.providers.docker.packages_history`**
(`record_package_inventory`, `has_changed`) is § 22's own write-on-change
shape, one subdirectory per subject, applied to a `{mechanism,
packages}` pair instead of a single string: a mechanism change alone
(e.g. `"dpkg"` to `"none"`) counts as a real change even when
`packages` happens to compare equal (both empty) — the mechanism that
answered is itself part of what this stream states.

**`aistack.timemachine.projection.docker_packages`**
(`project_docker_packages`) is an eleventh `aistack.timemachine.iri`
builder (`docker_packages_iri`, keyed by subject and recording instant
— the same reasoning `docker_digest_iri` already holds) and two new
predicates: `aistack:packageCount` (`XSD_INTEGER`, the same reasoning
`aistack:changeCount` already holds — a magnitude, not an identifier)
and `aistack:packageMechanism` (a plain string literal, the same
reasoning `aistack:imageDigest` already holds for a label). **The full
name/version list is deliberately not promoted to individual graph
facts** — § 21's own `aistack:changeCount` reasoning, doubled here: a
package inventory can hold not hundreds but potentially thousands of
entries, reachable through `aistack.cli.history_query` the same way
any other stream's raw content already is. No `aistack:occurredAt`,
the same restraint every 1.5 stream in this package already documents.
Wired into `aistack.cli.timemachine_rebuild.main` as the sixth
projection pass, after docker-digest, before collection gaps (which
stays last, unchanged).

**`aistack.cli.docker_packages_monitor`** is § 22's own governed
polling loop (`POLL_SECONDS = 10.0`, unchanged), R11 built in from its
first version, `--once`/`--dry-run` for a first manual check against
the real Docker daemon before enabling as a service. Its own console
log reports `{subject, mechanism, package_count}` per changed
subject, deliberately not the full package list — the same restraint
the projector's own module comment gives for the graph, applied here
to a human-facing summary instead.

**Built, tested, and wired end to end, 2026-09-28**:
`aistack.providers.docker.packages` (`collect_package_inventory`,
`collect_running_container_packages` — 9 tests, including the
dpkg-first/apk-fallback/neither-answers chain, sort-by-name, and a
malformed record being skipped on each mechanism);
`aistack.providers.docker.packages_history` (`record_package_inventory`,
`has_changed` — 11 tests, the exact shape § 22's own `digest_history`
suite already holds, plus the mechanism-alone-changes regression);
an eleventh `aistack.timemachine.iri` builder, `docker_packages_iri`;
`AISTACK_PACKAGE_COUNT`/`AISTACK_PACKAGE_MECHANISM` in `aistack
.timemachine.vocabulary`; `aistack.timemachine.projection
.docker_packages` (`project_docker_packages`, 11 tests, including the
same same-second-collision-aware regression every prior projector
suite already holds, and an empty inventory still being a real
observation with count zero); `aistack.cli.docker_packages_monitor`
(`parse`, checkpoint load/save, `log_cycle`, `run_cycle` — 21 tests,
real subprocess boundary mocked, real tmp-path files, the
checkpoint-still-advances-on-a-quiet-cycle and
dry-run-writes-nothing regressions every prior monitor suite already
holds); `deploy/systemd/aistack-docker-packages-monitor.service` and
`run_docker_packages_monitor.sh`, mirroring § 20–22's own
install/watch instructions. Full governed chain (`pytest`, `ruff check
src tests timemachine_ui`, `mypy`, `knowledge_integrity`) clean —
2527 tests passing (54 new), 536 source files.

`timemachine_ui`'s own generic node-facts view (§ 19) is expected to
render this stream with no new template code, the same open item §
21 and § 22's own entries already carry forward for the same reason
(`docker` unreachable from this verification host) — not yet
re-confirmed against a real batch from GIGABYTE's own Docker daemon.

With § 20 through this section, **1.5's four named Docker collectors
are all built, tested, and delivered**: `docker events`, `docker diff`
périodique, dérive du digest, inventaire des paquets. The roadmap's
own § 1.5 wording ("Trace également les upgrades sur les containers
docker") now has every raw fact a later interpretation layer needs to
attach a before/after image and package inventory to a detected
upgrade — see the *Open Points* entry below, updated the same day.

### 24. Ruban du temps — a v1 slice of maquette 1, 2026-09-28

The owner's own 2026-09-28 decision, the same breath as § 23: pick the
first of maquette 1's own pieces back up now that both bitemporal data
(`aistack:occurredAt`, docker-events, § 20) and R11's own collection
gaps (§ 9's addendum) are real in the graph — the exact precondition
§ 18's own *Open Points* entry named this piece as blocked on.

A fresh cadrage (`AskUserQuestion`) settled the one real design
question before any code: **which streams get their own band.** The
owner's own decision, over narrowing this to the four 1.5 Docker
streams: every `prov:Activity` the graph currently holds, the same
generic-over-whatever-the-graph-holds philosophy `streams` (`/`) and
`tree_view` (`/tree`) already hold — a future stream needs no change
here to appear on the ribbon.

**A deliberately narrower v1 than the validated maquette — the same
restraint § 19's own graph view already exercised for maquette 2.**
The maquette's own wording ("ruban du temps, curseur d'instant,
pas-à-pas ; arbre du réseau ; ... ; fiche de l'événement avec panneau
« Pourquoi »") names five real pieces; this section ships one of them.
**Built**: a single, chronological, per-stream-filterable list of
every recorded instant in the graph — every real "bande par historique
(masquable)" the maquette asks for, plus its own colour-*and*-shape
badge per stream (never colour alone — the `dataviz` skill's own
categorical-identity rule), plus an honest label distinguishing a real
`aistack:occurredAt` from a `prov:generatedAtTime` recording-time
fallback, plus a plain distinction for a collection gap (R11) — itself
a real, dated graph fact, but one that states an absence, not an
observation, so it is tagged rather than shown as if it were one more
ordinary event. Every row links into `/node`, reusing the full
provenance drill-down § 19 already built rather than duplicating it.
**Not built, named here rather than left to discover**: the "curseur
d'instant, pas-à-pas" stepping control itself (this v1 is a full list,
browsed top to bottom, not a position stepped through one instant at a
time); the network tree shown paired alongside it (`/tree` already
exists as its own separate view — linking the two, or merging them
into one screen, is real future design, not attempted here); and the
event detail card's own "panneau Pourquoi", explicitly 1.7's own
concern already (`claude/SESSION-2026-09-28-1.4-arbre-et-graphe.md`).

**`timemachine_ui/app.py`** (`_ribbon_entries`, `ribbon_view`) — a
third route (`GET /ribbon`) and view, alongside `/` and `/tree`. One
SPARQL query across the whole store (widening `node`'s own per-stream
`instants` query to every stream at once) builds the merged,
time-sorted list; a second, small query over `aistack:collectionGap`
marks which entities are gaps. **Per-stream visibility, `masquable`,
is a GET query string, not client state** — the same stateless-
navigation convention `tree_view`'s own `q` parameter already holds,
consistent with this mini-app's own read-only, per-request
`OxigraphGraphStore.read_only` handle (§ *Decision* 10: no server-side
session this screen would otherwise have to keep). A hidden
`submitted` field in the filter form is what lets "every box
unchecked, on purpose" be told apart from "no query string at all" —
an empty `streams` list means something different in each of those
two requests, and a GET form has no other way to say which one this
is.

**No pytest coverage for this route**, the same `timemachine_ui`-wide
convention every other route in this file already holds (decision #9,
2026-08-29: FastAPI stays out of the governed venv, so `app.py` is
verified by real execution, never by the governed suite). Verified
this way, 2026-09-28: a real graph seeded from real collector output
(two `docker-events` with real `occurredAt`, one `docker-diff`
snapshot, one `docker-digest` observation, one collection gap on
`docker-events`), a real server started against it — five entries
rendered in the correct chronological order, each stream's own badge
colour consistent between its filter checkbox and every one of its
own rows, the collection gap correctly tagged and excluded from
looking like a normal `docker-events` entry, the per-stream filter
correctly narrowing the list, the "every box unchecked" and "no
filter at all" states correctly distinguished, a ribbon row correctly
following through to its own real `/node` page, and both languages
rendering their own distinct labels. `/tree`'s own pre-existing
dependency on a real Docker daemon (unrelated to this section) is the
one route this verification could not also exercise, the same
open item § 21 through § 23 already carry forward for the same reason.

`fastapi.Query` added to `pyproject.toml`'s own `extend-immutable
-calls` (`ADR-0011`'s own reasoning already covers `fastapi.Form` —
the same marker-object idiom, applied to a repeated query parameter).
Full governed chain (`pytest`, `ruff check src tests timemachine_ui`,
`mypy`, `knowledge_integrity`) clean, `2527` tests unchanged (this
route carries no pytest of its own, per decision #9) — the i18n
catalog's own static scan (`tests/unit/i18n/test_the_real_catalogs.py`)
is what actually exercises every new `timemachine.ribbon.*` key this
section adds, both languages, no missing or orphaned key.

### 25. La corrélation "upgrade" — 1.5.1's third and last named piece, linking two already-collected facts

The Open Points entry § 22's own closing note left open ("not yet
designed in any further detail... not yet built"), designed and shipped
here, 2026-09-28 — the same segment as § 23 and § 24, closing 1.5.1's
GUI scope in full.

A fresh cadrage (`AskUserQuestion`) settled the two real design
questions before any code:

1. **How the correlated fact appears in the graph.** The owner's own
   choice, over a view computed at read time: a new predicate,
   `aistack:upgradeCorrelatesWith`, written into the graph at
   projection time — interrogable in SPARQL the same way every other
   fact this ADR describes already is, rather than a shape only one
   particular reader (`history_query`, `timemachine_ui`) knows how to
   reconstruct.
2. **The pairing window.** The owner's own choice, over a bounded
   window (e.g. 24h each side): always the nearest `docker-packages`
   snapshot on each side of a detected digest change, with no time
   limit — `ARC-P-006`: no real measured gap yet exists to size a
   threshold from, and an unusually large real gap stays a visible,
   dated fact once queried (the two entities' own
   `prov:generatedAtTime` subtract), never a threshold silently
   hiding it.

**The trigger needed no new detection logic at all — it was already
implicit in § 22's own write-on-change contract.**
`aistack.providers.docker.digest_history.record_image_digest` only
ever writes when the new digest differs from the last one recorded for
that subject (§ 22's own decision). So every `docker-digest` instant
recorded for a subject *after* its own first is, by that contract
alone, already a genuine digest change — this module never re-opens a
digest observation's own value to compare it against the previous one;
`digest_history` already made that comparison once, at collection
time.

**`aistack.timemachine.projection.upgrade_correlation`**
(`project_upgrade_correlation`) — a projection pass unlike every one
before it in this package: it links two already-projected
`docker-packages` entities together rather than collecting a new
source stream of its own, so it mints no new `prov:Activity` (the same
restraint `aistack:partOf`/`aistack:explains` already hold for a
predicate between existing entities). It walks both `docker-digest`
and `docker-packages` subject trees directly (the same `rglob`-based
walk every write-on-change stream's projector in this package already
holds, generalised here into one function serving both), re-validating
each side's own shape independently (`{"digest": str}`;
`{"mechanism": str, "packages": list}`) before treating an instant as
a candidate — so this module never links to an IRI the stream's own
projector itself declined to emit. `aistack.cli.timemachine_rebuild`
runs it seventh, after both `project_docker_digest` (fifth) and
`project_docker_packages` (sixth) — the two entities a correlation
links already have to exist before this module can link them — and
before `project_collection_gaps` (now eighth, unchanged in its own
reasoning for running last).

11 new tests (2527→2538): `test_project_upgrade_correlation.py` (10 —
no root, only-digest-root, only-packages-root, a first digest
observation is not itself a change, one change correctly bracketed,
two changes each picking their own nearest pair, a change with no
packages before/after it left uncorrelated, a subject with digest
history but no packages history entirely skipped, a subject name
embedding `/`) plus one `test_timemachine_rebuild.py` case exercising
the three new printed lines end to end through the real CLI. Every
timing-sensitive test pins real instants through the same frozen-
`datetime` monkeypatch `test_project_docker_packages.py`'s own
write-on-change test already established, rather than "a second
apart" — nearest-neighbour pairing needs controlled, known instants to
verify precisely.

**Caught before committing**: this section was first built against a
stale scratch clone (`1aee28a`, missing § 24's own already-pushed
commit) — `git stash` before a `git fetch && git reset --hard
origin/main`, then `git stash pop`, corrected it cleanly before any
patch was generated, the same `origin/main`-drift discipline every
patch this segment has already followed.

Full governed chain (`pytest`, `ruff check src tests timemachine_ui`,
`mypy`, `knowledge_integrity`) clean against the real current
`origin/main` tip (`d71e79a`, § 24's own commit).

### 26. Ruban v2 — a real time axis, a navigation cursor, and the charte graphique the mini-app never got

The owner's own question, 2026-09-29, the morning after 1.5.1 closed:
what technology would actually close the gap between § 24's v1 slice —
a plain `<ul>` of bordered cards — and the four validated maquettes'
own visual finish, and why had `timemachine_ui` never received the
navy/Georgia charte graphique `SESSION-2026-09-26-charte-graphique-
persiaut-1.1.1.md` already gave `console.html`/`architecture.html`/
`health.html`? The honest answer to the second question: the mini-app
did not exist yet on 2026-09-26 — nothing to retrofit, not an
oversight.

**A fresh cadrage (`AskUserQuestion`) settled two real design
questions before any code.** First, rendering technology: SVG plus
inline vanilla JS, no vendored library and no CDN — the owner's own
choice, over vendoring a second charting library the way `mermaid.min
.js` is already vendored, because a general-purpose chart widget would
carry its own visual opinions likely to diverge from the validated
maquette's own precise marks/colours rather than respect them, and
because this heritage already holds exactly the zero-dependency, self-
contained-per-page discipline SVG + vanilla JS needs, nothing new to
justify. Second, whether to fold the charte graphique retrofit into
the same patch: yes, in the same effort, rather than as a separate
one later.

**A second, narrower cadrage settled the one point still open after
those two**: what the "curseur d'instant, pas-à-pas" the maquette
names should actually do, given that maquette 3 ("reconstituer en
trois clics") — the feature the cursor exists to drive — has no
backend at all yet, not one route. Building a cursor that moves but
triggers nothing would be decoration, exactly what `ARC-P-006`
forbids. The owner's own decision: give it real, if narrower,
behaviour today — click, or releasing a drag, opens the nearest
instant's own `/node` card, the drill-down § 19 already built — rather
than ship nothing, or ship a reconstruction backend nobody asked for
yet.

**Built:**

- `aistack.renderers.timemachine.ribbon_svg` (`RibbonMark`,
  `RibbonSvg`, `render_ribbon_svg`) — pure, deterministic geometry, the
  same `href`-arrives-pre-built contract `ProvenanceNeighbor` already
  holds. One lane per stream, in the caller's own already-sorted
  order (a lane's row never reshuffles when a filter hides another
  stream); a linear time scale from the earliest to the latest visible
  instant, degenerating safely to the lane's own midpoint when every
  mark shares one instant (no division by zero); every mark keeps its
  existing colour-and-shape badge (never colour alone), now positioned
  by real time instead of stacked in a flat list; a gap entry (R11)
  gets its own CSS class and says "enregistré"/"occurred" honestly in
  its own tooltip exactly as the flat list already did. Hover uses
  SVG's own native `<title>` element inside each mark — a real,
  correctly positioned tooltip in every browser, satisfying the
  `dataviz` skill's own hover-layer requirement without one line of
  hand-rolled positioning JS to get subtly wrong.
- `timemachine_ui/templates/ribbon.html` — the SVG sits above the
  existing `.band-list`, which stays exactly as it was: the `dataviz`
  skill's own non-negotiable, "a table view exists," and every mark's
  `<a href>` keeps working by keyboard or a screen reader with no
  script running at all. One small, hand-written, static `<script>`
  (never regenerated per request) reads a JSON data island
  `render_ribbon_svg` emits next to the `<svg>` and wires the cursor:
  `mousedown`+`mousemove` previews a position, `mouseup` (a plain click
  is a `mousedown`/`mouseup` pair with no movement between them) snaps
  to the nearest mark and navigates — never mid-drag, which would spam
  navigations.
- `timemachine_ui/templates/_style.html` — charte graphique retrofit:
  every accent that was still the pre-charte generic blue `#1f6feb`
  (back-link, view-switch, tree-search/ribbon-filter buttons, the tree
  node's own historique badge) is now `#16335c`, and page headings
  (`header h1`) now carry the same Georgia stack `console.html`'s own
  titles already do — values copied from the same already-verified
  source every other renderer's charte comment cites
  (`aistack.renderers.console.html`), not re-sampled. A button's hover
  state uses `filter: brightness(.85)` rather than inventing an
  unverified darker hex the way the old `#1f6feb`→`#1858c4` pair once
  did — computed, not guessed, the same discipline the charte
  session's own colour work already held ("pas devinées"). New ribbon-
  specific rules (`.ribbon-svg`, `.ribbon-lane-line`, `.ribbon-axis-
  line`, `.ribbon-cursor`, …) scale with the SVG's own `viewBox` at
  `width: 100%`, reaching the same 700px/480px breakpoints (R12) as
  everything else on this shared stylesheet without a media query of
  its own — though lane labels do shrink to a genuinely small size on
  a narrow phone, named here as a real, not-yet-refined limitation
  rather than left to discover.
- Two new translation keys (`timemachine.ribbon.list_heading`, and a
  rewritten `intro` naming the cursor and the still-open panel/tree
  gaps honestly) in both `catalogs/fr/timemachine.yml` and
  `catalogs/en/timemachine.yml` — the closed set every localized
  screen's own test already enforces.

11 new tests (2538→2549): `test_ribbon_svg.py` — no streams and no
marks still render a real axis, not a crash; every box unchecked still
draws empty lanes; a single mark lands at its lane's own midpoint with
no division by zero; two marks on one stream share one lane line; two
streams keep their own given lane order; the earliest and latest
instant both get an axis label; every mark sharing one identical
instant still renders without dividing by zero; a gap entry gets its
own CSS class; a recording-time fallback says "enregistré" in its own
tooltip rather than being presented as a real occurrence; marks emit
the cursor script's own JSON data island; a stream name carrying
markup characters is escaped in its own lane label. No test touches
`timemachine_ui/app.py` itself or the hand-written cursor script — the
same decision #9 convention (2026-08-29) every other route in this
file already holds (FastAPI stays outside the governed venv), extended
here to the one JS file this mini-app now ships.

**Verified beyond the governed suite, the same way patch 0025's own
charte graphique work already was**: a standalone Jinja2 render (no
FastAPI, no running store — `aistack.renderers.timemachine.
render_ribbon_svg` and `aistack.i18n.web.page_language` are both
framework-free) against a fabricated fifteen-mark, five-stream graph,
screenshotted with Playwright/Chromium at 1000px and 375px widths, and
a scripted `page.mouse` click and a drag-then-release, each intercepted
before navigating, both confirmed to resolve to the nearest mark's own
`href` — a plain click near the earliest `docker-diff` mark opened
exactly that instant; a drag ending near the `observation` lane's
rightmost mark opened exactly that one, snapping on release, not
mid-drag.

**Deliberately still narrower than the validated maquette — the same
restraint § 24 and § 19 already exercised.** Not built here, named
rather than left to discover: the network tree shown paired alongside
the ribbon (`/tree` stays its own separate view); the event card's own
"panneau Pourquoi" (1.7's own concern, unchanged); maquette 3's actual
reconstitution, which the cursor deliberately does not attempt; touch
drag on a phone (every mark's own `<a href>` still works by a plain
tap, with or without the cursor script); and a mobile-specific lane
layout wider than the shared stylesheet's existing scaling already
gives it for free.

Full governed chain (`pytest`, `ruff check .`, `mypy`,
`knowledge_integrity`) clean against the real current `origin/main`
tip (`a8556c7`, patch 0080's own commit).

**Second slice, 2026-09-29 — real production data found two more real
gaps, grounded in the owner's own screenshot of `/ribbon` in use, not
guessed.** Roughly twenty real streams exist today, not the five or
six the v1 slice above was designed against: crowded lane labels, and
several close instants on one lane — `docker-events` worst of all —
rendering as one illegible, overlapping smear. A fresh cadrage
(`AskUserQuestion`) settled two more decisions before any code, plus a
priority order and an audit-first plan for the screens beyond the
Time Machine:

1. **Streams group by category, foldable** — not an invented
   taxonomy: the only two kinds of stream this graph's own code
   distinguishes are the four 1.5 Docker collectors (each its own
   dedicated projector module, each declaring its own `STEM`
   constant — `docker_events`/`docker_diff`/`docker_digest`/
   `docker_packages`) and everything else, which shares the exact same
   generic `project_observation_history` walk and the exact same
   `stream_iri` scheme. `timemachine_ui.app`'s `ribbon_view` now
   partitions `all_streams`/`svg_marks` into `_DOCKER_COLLECTOR_STREAMS`
   and its complement, and calls `render_ribbon_svg` twice — once per
   category, each its own independent local time axis (which
   incidentally also softens the uneven-distribution problem, since
   each sub-ribbon scales only to its own category's own min/max).
   `render_ribbon_svg` itself stays fully category-agnostic — the split
   is the web layer's own responsibility, the same reasoning
   `aistack.timemachine.iri`'s own docstring already states for
   staying prefix-agnostic. `ribbon.html` wraps each category's own SVG
   in a native `<details>`/`<summary>` disclosure, the same pattern
   `.tree-node` already uses for the network tree — both open by
   default, so folding is available without any instant becoming
   invisible by default.
2. **Marks too close together to tell apart merge into one counted,
   still-navigable cluster** — `_cluster_lane`/`_render_cluster` (new,
   `ribbon_svg.py`) group a lane's own marks, sorted by pixel position,
   into runs where each mark sits under `_CLUSTER_MIN_GAP_PX` (14px) of
   the one immediately before it in the same cluster — a chained
   distance, not a fixed window, so a long run of close marks collapses
   into one cluster even when its own first and last members are
   further apart than the threshold from each other. A cluster's own
   glyph carries its member count (`"●3"`); its `<title>` tooltip names
   every member's own stream/instant/subject line, never averaging one
   away; its `href` still opens a real `/node` card (the earliest
   member's) — never a dead link. **Narrower than the option's own "qui
   se déplie" (unfolds in place) wording, named here rather than left
   to discover**: this slice does not unfold a cluster back into its
   individual marks in place — the same restraint already applied to
   the cursor's own real-but-narrower scope above. Every clustered
   instant stays fully visible, unclustered, in the flat `.band-list`
   this screen already keeps beneath the graphic.

The cursor script (`ribbon.html`'s own static `<script>`) now wires
every `.ribbon-svg` on the page independently — `document
.querySelectorAll` paired with each SVG's own sibling `.ribbon-marks-
data` data island (via `nextElementSibling`) — rather than the v1
slice's singular `getElementById` lookup; a category with zero visible
marks emits no data island at all and is skipped, never a crash. Each
SVG's own nearest-instant search stays scoped to its own marks: a
cursor in one category's picture never jumps to the other's.

Two new translation keys (`timemachine.ribbon.group_docker`,
`timemachine.ribbon.group_observation`) in both catalogs.

5 new tests (2549→2554) in `test_ribbon_svg.py`: two marks a second
apart on a day-long axis merge into one cluster (and only two cursor
points are emitted, not three); a clustered mark still names every
member in its own tooltip; a cluster still navigates to a real node,
never a dead link; marks genuinely far apart on a short axis do not
cluster; a cluster containing a gap still carries the gap's own CSS
class alongside the cluster's own. `timemachine_ui/app.py`'s own
category split stays outside the governed suite, the same decision #9
convention every other route in this file already holds.

**Verified beyond the governed suite, the same standalone Jinja2 +
Playwright pattern already used above**: a fabricated twenty-stream
graph (four Docker collectors, sixteen observation streams, a
six-member burst on `docker-events` three seconds apart) rendered
through both templates, screenshotted, and confirmed the burst renders
as one bold `"■6"` glyph rather than six overlapping marks. A scripted
click on the Docker group's own cluster opened its earliest member
(`docker-events:0`); a scripted drag across the Observation group's
own picture opened a mark from that group alone — confirming the two
groups' cursors never cross-navigate.

**Priority and next steps, the owner's own decision, 2026-09-29**: the
Time Machine screens (ribbon, tree, node, streams) are worked first,
before console/architecture/health — which already received the navy/
Georgia charte graphique retrofit (`SESSION-2026-09-26-charte-
graphique-persiaut-1.1.1.md`) but not yet a finish-level audit against
their own validated maquettes. That audit is a separate, not-yet-
started deliverable: findings first, no code changes to those three
screens until the owner has seen them. 1.5.2 (version bump,
`RELEASE-NOTES.md`, image publication per `OPS-0002`) stays gated on
the graphic debt — this slice, the remaining Time Machine work, and
the console/architecture/health audit's own findings — being caught up
and confirmed applied on both hosts, not on this slice alone.

**Third slice, 2026-09-29 — patch 0082 applied and published (both
hosts, `798c527`) within hours, and production immediately found two
more real gaps.** The owner's own screenshots of `/ribbon` after
applying it: (1) the whole page still sits in a fixed narrow column no
matter how wide the browser window is — `900px` on every Time Machine
screen and on `console.html`/`health.html`, `1100px` on
`architecture.html`, none of it new to this slice; and (2) —
`ribbon_svg.py`'s own — `docker-events` alone carried 49125 real
instants in a roughly four-hour window, which the second slice's own
clustering chained into one glyph labelled `"●49125"`, and
`resource-priority-decision`'s own dozens of smaller clusters sat
close enough that their own multi-digit count labels (`"22"`,
`"3353"`) visually ran into each other even though the underlying
marks stayed more than `_CLUSTER_MIN_GAP_PX` apart. The owner read the
second symptom as broken timestamps at first — they are cluster
counts colliding, not instants, an honest misreading this slice's own
fix should make impossible to have again.

A fresh cadrage (`AskUserQuestion`, 2026-09-29) settled both, together,
as one patch:

1. **Every screen adapts to the available window width** — the
   owner's own broader answer, "toute l'appli," not the ribbon alone.
   `max-width: min(96vw, 1600px)` replaces the fixed `900px`/`1100px`
   column on all four Time Machine screens (`timemachine_ui/_style
   .html`) and on `console.html`/`architecture.html`/`health.html`
   alike (`architecture.html`'s own `1100px` carried no stated
   rationale for being wider than the other two static pages, so it
   converges to the same rule rather than staying a bespoke
   exception). `ribbon_svg.py`'s own `_VIEWBOX_WIDTH` grows from 900
   to 1600 in step, so the extra room actually reaches the geometry
   this module computes, not only the CSS stretching the same cramped
   layout across more physical pixels.
2. **Clusters space themselves by their own real label footprint, and
   a lane too dense to plot honestly gets one summary badge instead**
   — the owner's own combined answer, treating what looked like one
   ask ("les horodatages à corriger") as the two real, separate causes
   it actually was. `_cluster_lane` (`ribbon_svg.py`) now runs a
   second, label-aware coalescing pass on top of its own first,
   position-only one (unchanged): `_estimated_label_width` gives a
   deliberately conservative per-character estimate of a cluster's own
   rendered text (no browser is available to this pure module to ask
   for a real text metric — `R5`'s own "logic in `src/`, tested"
   constraint), and adjacent clusters whose own estimated footprints
   would still overlap once drawn keep merging until a full pass makes
   no further change. Separately, `_lane_needs_summary` catches what
   the label-aware pass cannot: a single cluster swallowing more than
   `_LANE_SUMMARY_MEMBER_THRESHOLD` (50 — far beyond any close-in-time
   burst this heritage tested before this slice, the largest
   deliberately tested being 6, and cleanly below the smallest real
   production count found the same day, 49125) means no pixel position
   on that lane means anything any more; that whole lane then renders
   as one honest `_render_lane_summary` badge — a real total count and
   a real earliest/latest instant, still linking to a real `/node`
   (the earliest member's), drawn as a pill (a background `<rect>`) so
   it reads as clearly different from an ordinary mark or cluster,
   never a fabricated position and never a dead link.

4 new tests (2554→2558) in `test_ribbon_svg.py`: two clusters more
than the position-only gap apart still merge once their own two-digit
labels would overlap; a 60-member burst renders one honest summary
covering the whole lane rather than one illegible mega-cluster glyph;
and, testing `_lane_needs_summary` directly rather than through a
fragile pixel-exact reconstruction of `render_ribbon_svg`'s own public
positioning (this heritage's own precedent for a private geometry
helper when the alternative is that fragile) — 70 individually
reasonable two-member clusters still overflow the available width,
and a handful of them comfortably fit.

**Verified beyond the governed suite, the same standalone Jinja2 +
Playwright pattern already used twice above**: a fabricated graph
carrying 5000 `docker-events`-style instants in a four-hour window and
400 `resource-priority-decision`-style instants over 25 days,
screenshotted at 1800px width — the 5000-instant lane renders as one
clean `"5000 événements"` pill rather than an illegible number, the
400-instant lane the same via the member-count path, and the page's
own content area now spans nearly the full browser window instead of
sitting in a narrow fixed column.

### 27. Exec noise left out of `docker-events`, package inventory taken once per image (2026-10-02)

**Measured before any code, on the reference host.** Four days after
§ 20 shipped, the `docker-events` stream held 34,488 history files
(4.7 GB). One hour of it: 18,074 events, 97 % of them `exec_create`/
`exec_start`/`exec_die` — about 3,800 runs of containers' own declared
healthchecks (gluetun, MariaDB, frigate, curl/wget probes) and 2,338 of
AIStack's own `docker exec` package probes (§ 23's `dpkg-query` and
`/lib/apk/db/installed`, run in every container every 10 seconds). The
one real fault that hour held — `arrstack/mularr` restarting every 17
seconds, its SQLite database on NFS — was 432 lines among 18,074.

**Owner's cadrage, two decisions:**

1. **`docker-events` keeps a human or external `docker exec` and drops
   the two automatic kinds** — not every exec (which would lose exactly
   the manual action § 20 exists to trace), and not merely two of its
   three events. `ExecNoiseFilter` (`aistack.providers.docker.events`)
   drops an exec whose command is one of the package collector's own
   (`DPKG_QUERY_COMMAND`/`APK_DB_COMMAND`, imported from
   `aistack.providers.docker.packages`, never copied) or the
   container's own declared healthcheck (`Config.Healthcheck.Test`,
   read once per container through `docker inspect` and cached:
   `CMD-SHELL x` appears as `<shell> x`, `CMD a b` as `a b`).
   `exec_die` names no command, so the filter remembers the `execID`s
   it dropped, for the whole monitor run. It never drops what it cannot
   prove is noise: a container Docker could not inspect, or an
   `exec_die` whose creation this process never saw, is kept.
2. **`docker-packages` inventories a container once per image** —
   once at startup, then only when its image digest changes
   (`collect_packages_on_image_change`), since its packages come from
   its image. A container reporting no digest is still probed every
   cycle. Given up, and said so: a package installed by hand inside a
   running container is not seen until its image changes or the
   monitor restarts.

**The history already accumulated — owner's decision, the same day,
once the filter was confirmed in production** (no new batch in the two
minutes after the restart, against one every 10 seconds before):
archived out of the stream and refiltered, never deleted.
`aistack.cli.docker_events_refilter` moves
`docker-events/history/docker-events/` whole into
`docker-events/archive/<name>/docker-events/` — every original byte
kept — then writes back, under each batch's own original filename, only
the events `ExecNoiseFilter` keeps, so the graph rebuilt afterwards
keeps each surviving event's real recording instant. A batch left with
no event is not written back. Because an archived event can name a
container id that no longer exists (recreated since by an image
update), the refilter also matches a healthcheck through the
healthchecks the *current* container of the same stable subject
declares — a stand-in the live monitor never needs, since it only ever
sees ids that exist. A subject whose container was removed altogether
leaves Docker nothing to vouch for: measured after the first refilter,
93,274 of the 107,637 events kept were `invoiceshelf/invoiceshelf`'s own
healthcheck (`sh -c curl … --fail http://localhost:…`), an abandoned
trial removed from the host that same day. For that case only, the owner
declares the command (`--healthcheck SUBJECT=COMMAND`) — the filter
never guesses one. This is the one place this stream's history is
rewritten rather than appended to; the archive beside it is what keeps
that honest. Run with the monitor stopped, then `timemachine_rebuild`.

**`docker diff` every 15 minutes, not every 10 seconds — owner's
cadrage, the same evening.** With the exec noise gone, `dockerd` still
sat above 100 % CPU: § 21's collector ran one `docker diff` per running
container (~59) every 10 seconds, for a stream that had recorded 1,760
changed snapshots in five days. Unlike packages, a container's
filesystem does drift during its life, so § 23's "once per image" does
not apply; the poll interval goes to 900 seconds instead. A monitor
restart still takes a first pass immediately.

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
- **The ribbon's v2 is real too, not only cadred** (2026-09-29, § 26):
  `aistack.renderers.timemachine.ribbon_svg` gives the time ribbon a
  real horizontal time axis and a navigation cursor (click or drag-
  release opens the nearest instant's own `/node` card — never a
  reconstruction, which has no backend yet), and `timemachine_ui`'s own
  screens finally carry the navy/Georgia charte graphique
  `console.html`/`architecture.html`/`health.html` already held since
  2026-09-26 — this mini-app simply did not exist yet on that date.
  Verified with a standalone, framework-free render plus a scripted
  Playwright click and drag, each confirmed to resolve to the correct
  nearest mark. The network tree pairing, the "why" panel, and
  maquette 3's actual reconstitution all remain open — see § *Open
  Points*.

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
  responsive layout (R12). **Its v1 scope was narrower than the four
  maquettes the roadmap already validated** (a time ribbon, a network
  tree, a "why" panel) — those assumed `aistack:occurredAt`, collection
  gaps and Explications, none of which the graph held yet at the time
  (1.4/1.5's own concern); building toward their visual richness ahead
  of that data would have been exactly the invented infrastructure
  `ARC-P-006` forbids. What shipped first reproduced `aistack.cli
  .history_query` from the graph — streams, the instants each
  recorded, the facts known about one instant, and the reverse edges
  (agent, causal request) the enriched three-of-four streams already
  carried. **Two of the four maquettes have since gained a real slice**:
  the network tree (§ 18) and, § 24, a v1 of the time ribbon — a
  chronological, per-stream, colour-and-shape-badged, gap-aware list,
  deliberately without its own "curseur pas-à-pas" stepping control or
  a network tree paired alongside it. ~~**Its own stepping control was
  still not built**~~ — **resolved, narrower than the maquette,
  2026-09-29** (§ 26): the ribbon's own cursor now opens the nearest
  instant's `/node` card on click or drag-release — real navigation,
  never the reconstruction maquette 3 asks for, which has no backend
  to drive it. **Still not built**: the ribbon/tree pairing; the "why"
  panel (1.7's own concern); and maquette 3 ("reconstituer en trois
  clics") itself, which has no named step in the roadmap at all yet.
  Named here so the gap between what was demoed and what has actually
  shipped stays stated, not silently left for whoever opens the
  remaining maquette pieces next to discover on their own.
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
- ~~**Correlated "upgrade" facts**~~ — **resolved, 2026-09-28** (§ 25):
  `aistack:upgradeCorrelatesWith`, written at projection time, links
  the nearest `docker-packages` snapshot before a detected
  `docker-digest` change to the nearest one after it, no time window
  (both cadré with the owner, `AskUserQuestion`, this same segment).
  `ARC-P-012`'s boundary still holds — § 20's raw collector reports
  what happened, never an interpretation of it; this is a separate
  projection pass, not a change to any collector. The trigger itself
  needed no new detection code: § 22's own write-on-change contract
  already means every `docker-digest` instant after a subject's first
  is a genuine change, by construction.
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
- ~~**The ribbon's own illegibility at real production scale**~~ —
  **resolved, narrower than the maquette, 2026-09-29** (§ 26's second
  slice, extended by its third the same day): the owner's own
  screenshot of `/ribbon` in use, roughly twenty real streams and a
  close-instant burst on `docker-events` rendering as one overlapping
  smear, found this gap; category grouping (Docker collectors vs.
  everything else, each its own foldable, independently-scaled
  picture) and chained mark clustering closed most of it. Applied to
  real production the same day, two more real symptoms surfaced at the
  true scale (`docker-events`' own 49125 instants, not the handful
  tested against): one cluster's own label swallowing the whole lane
  as a meaningless single glyph, and several clusters' own multi-digit
  labels visually running into each other even while comfortably apart
  by raw position — both closed by the third slice's own label-aware
  clustering pass and its lane-level summary fallback, and the whole
  page (this mini-app and the three static pages alike) now adapts to
  the real window width instead of sitting in a fixed narrow column.
  **Still not built**: a cluster (or a lane's own summary badge) does
  not unfold back into its own individual marks in place — every
  instant stays reachable only through its own `<title>` tooltip or the
  flat `.band-list` beneath the graphic, not a click on the glyph
  itself; and the lane labels' own genuinely-small mobile size (named
  above, § 26) is unchanged by either slice. The console/architecture/
  health screens' own finish level against their validated maquettes
  — asked about in the same conversation that found this gap — is a
  separate, not-yet-started audit: findings first, no code until the
  owner has seen them (the owner's own 2026-09-29 priority: Time
  Machine screens first).
