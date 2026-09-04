---
artifact:
  id: STD-0300
  title: Official Validation Suite
  type: System Specification
  semantic_type: Specification
  domain: Standards
  criticality: C2
  status: Published
  confidence: Reviewed
  version: 1.17
  owner: Foundation
  created: 2026-07-31
  updated: 2026-09-04

relations:
  references:
    - STD-0200
    - FDN-0003
    - FDN-0007
    - FDN-0008
    - FDN-0012
    - ADR-0009
    - OPS-0001
    - OPS-0003
---

# STD-0300 — Official Validation Suite

> Structured per STD-0200. That standard scopes itself to *component*
> specifications; this artifact specifies the system as a whole. Confirming that
> extension of scope, the identifier and the location is a governed decision.

---

## Provenance

Content originates from `docs/99-meta/NEXT-SESSION-TODO.md`, where the project's
acceptance criteria sat in an unowned working note.

**Version 1.0 (2026-08-14)** extracted the two validation sections and rewrote their
narrative objectives as measurable criteria. That extraction **silently dropped**:

- the *Expected workflow* chain of the energy-waste case;
- the technical evidence of the reference incident, including the system-call
  observations;
- the *Validated capabilities* lists of scenarios 1, 2 and 3;
- the four-way classification required of a sustainability finding;
- several items of the eight-point validation objective, compressed into fewer
  criteria than the original required.

**Version 1.1 (2026-08-14)** restores all of it. Nothing from the source note is now
absent from this artifact, apart from the two roadmap items — *Adaptive Resource
Scheduler* and *Knowledge Time Machine* — which are not acceptance criteria and
remain in `99-meta`.

The v1.0 omission repeated, at small scale, the defect of commit `76bd373`: content
removed during a restructuring without the change saying so. It is recorded here
rather than corrected in silence.

**Gravé — 2026-08-21.** This specification is governed heritage. What is engraved is an
*extraction*, not a reconstitution: the criteria come from a working note that still
exists in the repository, so this artifact can be checked against its source at any
time. That is why it carries less provenance risk than the three Foundation artifacts
engraved the same day. `confidence: Reviewed`.

---

## 1. Problem Statement

AIStack claims that infrastructure knowledge can be governed, explained and
transmitted. Nothing in the heritage stated how that claim is proven false.

Two questions motivate this suite:

- Can AIStack transmit its governed knowledge to an agent that has never seen the
  repository?
- **How can AIStack detect and eliminate unnecessary resource consumption?**

Without objective acceptance criteria, "AIStack works" is an opinion. That
contradicts the project's own position:

> Technical debt is not an opinion.
> It is derived knowledge produced from observations, evidence and explicit policies.

The same standard must apply to the platform itself (FDN-0008, Self-Application).

---

## 2. Purpose

Define the scenarios AIStack shall demonstrate, and the measurable conditions under
which each is considered satisfied.

These four scenarios constitute the **first official validation suite of AIStack**.

---

## 3. Responsibilities

This specification owns:

- the list of validation scenarios;
- the capabilities each scenario exercises;
- the acceptance criteria of each scenario;
- the recorded verification state of each criterion.

It does not own:

- how any scenario is implemented;
- the roadmap or the order in which scenarios are addressed;
- the classification or criticality model.

---

## 4. Inputs

- A running Docker host (VS-1, VS-4).
- A generated Context Bundle and its `manifest.json` (VS-2).
- A media catalog and a selection policy (VS-3).
- The runtime observations of the reference incident (VS-4).

---

## 5. Outputs

| Output | Nature |
|---|---|
| Knowledge Catalog of the observed infrastructure | generated |
| Boot Report produced by an onboarded agent | generated |
| Selection artifact | generated |
| Technical debt finding with its evidence references | generated |
| This specification | canonical |

All generated outputs are disposable (ENG-P-003). Only the criteria are governed.

---

## 6. Constraints

- **Reproducibility** — an unchanged input shall produce an identical output.
- **Explainability** — every statement produced shall be traceable to an observation
  or to an explicit policy.
- **Portability** — no criterion shall depend on a specific host, path or account.
- **Non-interference** — verifying a scenario shall not modify the governed heritage
  nor its published projection.

---

## 7. Functional Rules

- A scenario is satisfied only when **every** one of its criteria holds.
- A criterion that has never been executed is recorded as `not verified`, never as
  satisfied (FDN-0003 Article 12).
- A criterion shall be executable by someone who was not present when it was written.
- No scenario is satisfied by a human performing the reasoning on AIStack's behalf.
  The platform produces the finding, or the criterion fails.

### Expected chain of a sustainability finding

A finding produced under VS-4 shall follow this observable sequence. Each step
consumes the output of the previous one; no step may be skipped or inferred.

```text
Runtime Observation
        ↓
Process and Container Correlation
        ↓
Deployment Configuration Analysis
        ↓
Knowledge Policies
        ↓
Technical Debt Evaluation
        ↓
Sustainability Score
        ↓
Explainable Recommendation
        ↓
Human Validation
        ↓
Remediation
        ↓
Before / After Verification
```

Human Validation is a step of the chain, not a formality appended to it: the
platform proposes, the human decides (GOV-P-001).

---

## 8. Non-Functional Requirements

- Verification shall be automatable; a scenario requiring interactive judgement is
  not yet a criterion.
- Verification cost shall stay compatible with per-commit execution.
- Sustainability: VS-4 exists because resource waste is a governed concern, not a
  performance detail.

---

## 9. Acceptance Criteria

Each criterion carries its own state and, when it has one, the date its
verification was executed. A single date at the head of this section would have
to be rewritten at every change and would be wrong the moment one was missed —
which is how the sentence it replaces came to describe `45710f3` while the
criteria below had moved on. Last change: 2026-09-04, criteria 1.1, 1.2, 1.3,
1.4, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.5, 4.6, 4.7 and 4.8 (4.1, 4.2, 4.3, 4.5,
4.6, 4.7 and 4.8 advanced, not yet satisfied; 4.5's own wording was
corrected the same day).

### VS-1 — Docker Runtime Discovery

*Demonstrate that AIStack can automatically discover, model and document a Docker
infrastructure.*

Capabilities exercised: Runtime observation · Knowledge Catalog generation ·
Artifact generation · Infrastructure explanation.

| # | Criterion | State |
|---|---|---|
| 1.1 | Given a host running N containers, the generated catalog contains exactly N entries | **satisfied** — 2026-09-04 |
| 1.2 | Each entry carries identity, image, state, published ports and mounts | **satisfied** — 2026-09-04 |
| 1.3 | Regenerating from an unchanged host produces an identical catalog | **satisfied** — 2026-09-04 |
| 1.4 | Every statement in the generated explanation references an observation present in the catalog | **satisfied** — 2026-09-04 |

#### What 2026-09-04 verified, and what it did not

Executed against GIGABYTE, the production host, with no state change between the
two runs 1.3 compares.

**1.1 is satisfied.** `python3 -m aistack.cli.docker_catalog` produced a catalog
with 61 container entries; `docker ps -a --format '{{.Names}}' | wc -l` — the `-a`
matching what `DockerProvider.collect()` itself calls — independently counted 61.
Both readings taken from the same host state.

**1.2 is satisfied.** Every one of the 61 container entries carries `docker_id`,
`label`, `image`, `state`, `ports` and `mounts` — populated where Docker reports
something, and an explicit empty string rather than an absent key where it does
not (`cyberchef`, `gluetun`, `it-tools`, among others, carry `"mounts": ""`).

**1.4 is satisfied.** `docker-runtime-explanation.txt` was checked against the
catalog it was generated from: every field named in a sentence — image, state,
ports, mounts — is the value the corresponding `CatalogItem.metadata` carries for
that container, spot-checked on `jellyfin`, `sonarr` and the containers with no
mounts (rendered as `'no mounts'`, per `explain_docker_catalog`'s stated-absence
rule).

**1.3 failed twice before it was satisfied, and both failures were real.**
The first run found the `mounts` field's internal ordering unstable across
two `docker ps` invocations, for at least `bazarr`, `frigate`, `booklore`,
`beszel-agent`, `komga` and `filebrowser` — `DockerRuntimeCatalogBuilder`
joined Docker's `Mounts` field in the order Docker returned it, which
`docker ps` does not guarantee stable. Sorting that field closed it, but
the next live run found a second, independent cause: two entries of the
`images` family carrying the same `docker_id` — one image, two repository
tags, `rommapp/romm:latest` and `ghcr.io/rommapp/romm:latest` — swapped
position between two `docker images` observations with no host change.
Sorting `images` by identity closed that too. **Re-run against GIGABYTE,
2026-09-04, with `diag_catalog_diff.py` comparing every field of every
item rather than a single text diff: 0 field-level differences across 178
shared items, 178 items in both runs.** Neither ordering claim was a
guess — each was the literal cause a live diff named, fixed, and then
re-verified live rather than assumed fixed by the code change alone.

### VS-2 — Context Bundle / Self-Onboarding

*Demonstrate that AIStack can transmit its governed knowledge to another AI
instance.*

Capabilities exercised: Context Bundle generation · PROJECT-CONTEXT ·
NEXT-SESSION-TODO · Knowledge transfer · Self-Onboarding.

| # | Criterion | State |
|---|---|---|
| 2.1 | An agent given only the bundle produces a Boot Report carrying all eight declared sections | **satisfied** — 2026-08-14 |
| 2.2 | The agent states the bundle's `source_commit` and `content_hash` without external input | **satisfied** — 2026-08-14 |
| 2.3 | The agent identifies Gitea as the Acquisition SPOT and the mirrors as non-authoritative | **satisfied** — 2026-08-14 |
| 2.4 | Two agents of different models declare the same uncertainties and the same READY verdict | not verified |
| 2.5 | `aistack.cli.knowledge_integrity` exits 0 on the bundle used | **satisfied** — 2026-08-22 |
| 2.6 | The same report declares `clean: True` | **satisfied** — 2026-08-22 |

Criteria 2.5 and 2.6 make this scenario self-checking: the suite fails while the
heritage it transmits is itself unsound.

Both are executed by `tests/integration/validation/`, which regenerates the
projection and validates it at every run — § 11 asks that of any criterion that
becomes automated, so that a regression is visible per commit. The bundle is
written to a temporary directory: STD-0002 forbids a test from producing an
operational artifact.

**2.5 was recorded `failing` for eight days after its cause had gone.** The
blocking finding cited was `criticality-discrimination` — *no artifact is
declared C3* — noted on 2026-08-14. Artifacts declaring C3 have existed since
2026-07-24. Nothing distinguished that dead note from a live failure, because no
test ran the validator on the real projection; the two that existed built
synthetic bundles. Verified 2026-08-22 at `506230e`, and mutation-tested by
downgrading the fifteen C3 artifacts to C2, which reproduces the 2026-08-14
finding exactly.

**2.6 exists because measuring 2.5 exposed its limit.** The validator exits 0 on
warnings. Removing `owner` from one governed artifact yields `warnings: 1
clean: False` and an exit code of 0 — this scenario would pass while the heritage
it transmits had degraded. The `clean` field already carried that fact and
nothing read it. It is a separate criterion rather than a stricter 2.5 so that
*degraded* and *broken* keep different weights: a missing metadata field does not
carry the gravity of a heritage with no minimal governed context.

### VS-3 — Music Sync Selection Pipeline

*Demonstrate that the same Runtime architecture can orchestrate a business process
rather than infrastructure only.*

Capabilities exercised: Selection Pipeline · Catalog · Artifact generation · User
interaction · Regeneration.

| # | Criterion | State |
|---|---|---|
| 3.1 | The same catalog and the same policy produce the same selection | **satisfied** — 2026-09-04 |
| 3.2 | Every included and excluded item carries the rule that decided it | **satisfied** — 2026-09-04 |
| 3.3 | After a user modification, regeneration differs only by the modified items | **satisfied** — 2026-09-04 |

#### What 2026-09-04 checked, prompted by the owner citing 2026-09-03's Syncthing work

The owner considered VS-3 done, citing the previous day's `selection_ui` work
(hardlink materialisation, quota, Syncthing status). Checked against the three
criteria individually rather than accepted as one claim (§ 7 — a criterion is
recorded satisfied only through its own executed verification).

**3.3 is satisfied.**
`tests/unit/generators/test_hardlink_materialisation.py::test_unticking_removes_what_is_no_longer_designated`
materialises `["Classique"]`, regenerates with `["Classique/Bach"]` — the
user's modification — and asserts `report.removed == ("Classique/Berlioz/01.mp3",)`
and that only `Classique/Bach/01.mp3` remains under the target: the
regeneration changed exactly what the modification removed, nothing else.
`test_a_second_run_writes_nothing` reinforces it at the boundary case: an
unmodified selection, regenerated, writes nothing at all. Both tests run in
the governed suite, per commit.

**3.1 was closed the same day, by the missing test rather than a code
change.** `ByIdsSelectionStrategy.select()` was already pure and
sort-normalised — nothing in it explained a non-deterministic result — but
nothing had called the chain twice with the same inputs and compared.
`tests/unit/selection/test_the_selection_workflow.py::test_the_same_catalog_and_the_same_policy_produce_the_same_selection`
now does, through the full chain a real caller uses — catalog → view (built
twice, independently) → selection — and a third time with the policy's
identifiers given in a different order, since the same policy should not
depend on the sequence a caller happened to list it in. All three
`Selection`s compare equal.

**3.2 is satisfied, closed by a derived explanation rather than a change to
`Selection`.** The gap was real: `Selection` carries `selected_ids` and a
flat `metadata` dict, nothing per-item, and an item nobody ticked left no
trace to explain. Rather than thread a rule field through `Selection`
itself — which is persisted to YAML and already holds the owner's live
118 Gio selection on GIGABYTE, so a schema change there is a migration, not
a patch — `explain_selection(catalog, resolution)`
(`src/aistack/selection/explanation.py`) walks `catalog.items` directly and
names, for every one, the `SubtreeResolution` category that decided it:
`ticked` (a root), `inherited from '<root>'` (a covered descendant),
`redundant, already covered by '<root>'` (ticked but already covered), or
`excluded, never ticked and no ticked ancestor`. Nothing here is a new
judgment — `SubtreeResolution` already computed and already tested each
category; this only names what each one means, the same relationship
`explain_docker_catalog` had to the catalog it explained for VS-1's 1.4.
Seven tests in `tests/unit/selection/test_selection_explanation.py` cover
all four rules, assert every catalog item receives exactly one decision
(`test_every_catalog_item_gets_a_decision`), and confirm a ticked identifier
absent from the catalog is not fabricated into one
(`test_an_absent_ticked_identifier_is_not_a_catalog_item_to_explain`).

**VS-3 is the second scenario satisfied in full**: 3.1, 3.2 and 3.3 all
hold.

### VS-4 — Sustainability & Technical Debt Analysis

*Demonstrate that AIStack can derive technical debt and sustainability issues from
runtime observations.*

#### Reference incident

The permanent `aistack-selection-ui` service consumed approximately 50 % of one CPU
core while idle.

Evidence collected:

- no incoming HTTP requests;
- no active browser session;
- continuous filesystem traversal;
- Uvicorn started with `--reload`;
- the complete Git repository mounted into `/app`.

System-call observation showed repeated `newfstatat`, `getdents64`, `openat` and
`fstat` calls.

**Root cause** — the development-only Uvicorn reload mechanism continuously
monitored the mounted repository.

**Remediation** — remove `--reload` from the permanent container command and rebuild
the image.

**Measured result** — before: 48–58 % of one CPU core; after: 0.32 % of one
core, measured after two minutes of inactivity
(`docker-compose.selection-ui.yml`'s own comment) — a reduction of 99.4 %
from the upper bound.

The incident was diagnosed and remediated by a human. That satisfies no criterion
below: the point is that AIStack reproduces the reasoning.

#### Criteria

| # | Criterion | State |
|---|---|---|
| 4.1 | AIStack detects abnormal idle resource consumption without being pointed at the service | not verified |
| 4.2 | The finding correlates process, container and deployment definition, each with an observation reference | not verified |
| 4.3 | It identifies the development option enabled in a permanent service | not verified |
| 4.4 | Technical evidence is collected and attached to the finding, down to system-call level or equivalent | not verified |
| 4.5 | Each qualification the evidence supports, among technical debt, deployment misconfiguration, energy inefficiency and sustainability anomaly, is cited to a distinct policy; more than one found together is what makes the finding derived knowledge rather than an opinion about severity | not verified |
| 4.6 | The root cause is explained, derived from the collected evidence | not verified |
| 4.7 | A safe remediation is recommended, citing the policies it derives from by identifier | not verified |
| 4.8 | Before/after verification measures a CPU reduction ≥ 95 % (observed: 58 % → 0.32 %, 99.4 %) | not verified |
| 4.9 | No finding is emitted without at least one evidence reference | **satisfied** — 2026-08-22 |

Criterion 4.5 is not a formality. A single label would make the finding an opinion
about severity; more than one qualification, each traceable to a distinct policy,
is what makes it derived knowledge instead. Reworded 2026-09-04: the criterion no
longer reads "simultaneously as [all four]" — the reference incident, examined by
the owner against the full vocabulary, carries three of the four and explicitly
not the fourth (`OPS-0004`), and a criterion that its own reference incident could
never satisfy was wrong, not the incident.

#### What 2026-08-22 verified, and what it did not

The runtime qualification chain decided by ADR-0009 ran for the first time on
2026-08-22 against the reference deployment: 62 containers examined, none
unobserved, the signatures of `OPS-0001` applied to each.

**4.9 is satisfied by construction and was exercised.** `RuntimeFinding` refuses
to be constructed with empty evidence, and the refusal is mutation-tested — the
invariant was removed, the test failed, the invariant was restored. The control
run of 2026-08-22 produced one finding carrying eleven log entries, each
identified by an offset counting back from the newest line and by the timestamp
Docker recorded. Verified at `9e27da3`.

**4.1 remains `not verified`.** The chain detects *without being pointed at a
service*: run with no argument, it examines every container the host declares,
which is what the criterion asks and what the ancestor could not do —
`analyze_container` required a container name. Until 2026-09-04 the rest was
untouched: this chain read logs and measured no resource whatsoever. The
reference incident above is a CPU consumption diagnosed through system-call
observation, and nothing in the heritage observes system calls yet.

**2026-09-04 — resource measurement exists, and it reproduces the shape of the
reference incident, not only its symptom.** `DockerProvider.collect_cpu_readings`
calls `docker stats` with no container named — the same "every container, no
argument" mechanism `runtime_diagnose` already uses for logs — and
`aistack.runtime.idle_consumption.find_unexplained_consumption` flags a reading
against `resource_priority.yml`: any container absent from both `priority` and
`background`, at or above a threshold, is unexplained. `aistack-selection-ui`
was exactly that shape at the time — 48-58 % of one core, declared nowhere —
and `test_an_undeclared_container_over_threshold_is_flagged` proves the
function reproduces it; `runtime_diagnose` carries the wiring end to end,
proven the same way `4.7`'s CLI wiring was: a full sweep, no container named.

**What is still missing is named, not hidden.** This detects "elevated and
undeclared", not "idle" — nothing here distinguishes a legitimately busy,
merely unclassified container from one wasting resources at rest, because that
distinction needs the evidence 4.2 and 4.4 ask for (no incoming requests, no
active session, system-call observation), none of which exists yet. A
container doing real, undeclared work today would be flagged the same as a
`--reload` bug would be — correctly unexplained, not yet correctly diagnosed
as abnormal. `DEFAULT_THRESHOLD_PERCENT` (5 %) is a proposed starting number,
the same kind of guess `CpuThresholdDetectorDefinition`'s 50 %/15 s was,
chosen to be sensitive rather than fitted to the one incident measured — not
yet checked against a live sweep of containers nobody has classified.

**2026-09-04, later the same day — the first live positive.** A full sweep
on the reference deployment (61 containers examined) flagged exactly one:
`firefly` at 6.7 %, undeclared in either `priority` or `background`.
Investigated live — repeated `docker top`, a 60-second `docker stats`
sample, `docker logs`, `docker inspect` — the reading was not a
`--reload`-shaped bug: it was PHP-FPM answering a recurring health probe (a
monitoring tool hitting Firefly III's `/register` endpoint, a full Laravel
page render, roughly every 70 seconds), which produced the bursty pattern
the CPU sample showed rather than a flat plateau. The owner classified
`firefly` in `background` (`resource_priority.yml`, the file's own
documented "or by hand" path) once the shape was understood — the exact
ambiguity this paragraph named above, resolved for one real container
rather than guessed at.

**4.2 remains `not verified`, and it is now scoped rather than merely
absent.** Literally: "the finding correlates process, container and
deployment definition, each with an observation reference." Until
2026-09-04 nothing correlated anything — 4.1 and 4.3 each produced their
own finding, independently, citing one observation apiece.

`CorrelatedFinding` (`src/aistack/contracts/correlated_finding.py`) carries
all three, and `aistack.runtime.correlation.correlate_findings` builds one
per container that 4.1 or 4.3 already flagged — never a fresh sweep, since
`docker top` takes one container at a time and correlating all 61 regardless
of whether anything was found would answer a question nobody asked.
`DockerProvider.collect_process` reads the container's own live PID
namespace (`docker top`), independent of `collect_commands`'s configured
read; `deployment_definitions()` reads the two Dockerfiles this repository
actually builds and extracts their `CMD`. `test_a_named_container_is_
correlated_from_all_three_maps` proves the stitch; `runtime_diagnose` reports
each of the three with its own reference, `deployment` printing `undeclared`
rather than a guess when none exists.

**The scope, decided with the owner 2026-09-04:** a deployment definition is
readable only for `aistack-core` and `aistack-selection-ui`. The other ~60
containers on the reference deployment are deployed and managed entirely
outside this repository — `frigate`, `gluetun`, the *arr suite — and no path
exists here to read one for them. `CorrelatedFinding` declares that state
explicitly (`deployment_command`/`deployment_reference` both `None`) rather
than inventing a source, per `GOV-P-001`; extending the mapping happens when
the owner names where a definition actually lives, not before.

**4.3 remains `not verified`, and 2026-09-04 acquires most of it.** The
criterion, literally: "it identifies the development option enabled in a
permanent service." `DockerProvider.collect_commands` reads every container's
own launch command with `docker ps --no-trunc` — untruncated, unlike
`collect()`'s own call, which never read `Command` at all before today — and
`aistack.runtime.development_flags.find_development_flags` matches it against
`KNOWN_DEVELOPMENT_FLAGS`: one declared pattern, `--reload`, which is the
literal cause of the reference incident. `test_a_reload_flag_is_reported`
proves the CLI reads a command carrying it and reports it; `runtime_diagnose`
carries the wiring, no container named, the same shape 4.1 and 4.7 already
established.

**What is not yet acquired: "permanent".** Nothing here reads whether a
service is meant to run continuously — every container's command is checked
alike, and a one-off container legitimately started with `--reload` for a
human's own use would be flagged the same as a permanent one wrongly left
running with it. That distinction is `OPS-0003`'s own territory
(`continuous`/`intermittent`), not yet connected to this finding. `--reload`
is also the only pattern declared: `GOV-P-001` holds here as it does for
`OPS-0001`'s signatures — a second pattern is added once a second real case
names one, not guessed at now.

**4.7 remains `not verified`, and the gap has a name.** A finding does cite the
policy that produced it — `OPS-0001/S-004` — which is the citation the criterion
asks for. But every signature in `OPS-0001` declares `grounding: unknown`, and
that field names precisely the policy that would make the *remediation* the right
one. "Check the target service, the exposed port, and the Docker network"
presupposes that a dependency between two services is declared somewhere in this
heritage, and none is. The field was added on 2026-08-22 to make that absence
countable under FDN-0003 Article 12; using its existence to declare the criterion
satisfied would turn an instrument of visibility into a way of hiding what it
measures. This criterion moves when a remediation policy is written, not before.

**2026-09-04 — a remediation policy was written, for one subject.** `OPS-0003`
declares `frigate` as `intermittent`, in the owner's own words: stopped most of
the time to save resources, started back up on demand. `ground_findings`
(`src/aistack/runtime/grounding.py`) reads that register after `qualify()` and
adds the owner's context to any finding whose subject `OPS-0003` names, citing
`OPS-0003/frigate` rather than `unknown` — verified end to end,
`test_the_frigate_finding_is_grounded_after_qualification`, from a real
`OPS-0001/S-004` qualification through to the grounded citation.
`aistack.cli.runtime_diagnose` carries the same wiring — every finding it
reports is grounded against `OPS-0003` before printing — so the next live
sweep on the reference deployment is where this reaches a real host rather
than only a fixture.

**This is not the criterion satisfied, only advanced.** `4.7` reads on *a safe
remediation*, singular in form but general in the state it describes — every
signature `OPS-0001` declares still presupposes an undeclared policy for any
subject it has not been told about, and `S-001`, `S-002` and `S-003` are
untouched by this: no fact has been given yet for a VPN credential's declared
location, or for a dependency between two services. `test_every_governed_
signature_declares_its_grounding_as_unknown` still passes, deliberately — the
signature was not the thing to change. One finding, for one container, on one
declared fact, now carries a real citation instead of `unknown`; the criterion
stays `not verified` until that is true of what it asks for generally, not of
one case that happens to be provable today.

**4.6 remains `not verified`, and this session names what closing it
needs.** The criterion, literally: "the root cause is explained, derived
from the collected evidence" — read against VS-4's own header, "AIStack
can derive," not a human reading AIStack's output and reasoning about it
in conversation. The `firefly` investigation above is the first case
where a root cause was actually derived from evidence rather than
assumed, and it is worth recording precisely what that took, because none
of it exists in `aistack` today: 4.2's correlated evidence (container
command, live process, deployment definition) narrowed the *subject* —
s6-overlay, PHP-FPM, nginx, nothing custom — but did not, by itself,
explain *why* CPU rose. Two further evidence types did, neither collected
by any current provider or detector: a CPU reading taken repeatedly over
a window, to tell a plateau from a burst (`docker stats --no-stream`,
called by hand, twelve times); and the container's own access log, read
for a repeating request pattern tied to one external actor's identity (a
`User-Agent` naming a monitoring tool). The derivation itself —
recognising that a ~70-second request cycle and a bursty CPU sample
describe the same cause — was done by a human reading both together, in
one conversation, not by any function in this repository.

Building a generic root-cause deriver from one case would repeat the
mistake `GOV-P-001` and `ARC-P-006` already guard against elsewhere in
this section: `firefly`'s cause (an external HTTP health-check hitting a
heavy endpoint) is a plausible shape for a second case, not yet a
confirmed pattern — the same discipline that kept
`KNOWN_DEVELOPMENT_FLAGS` to one entry after the reference incident
applies here. What moved today is the evidence this criterion is scoped
against: time-series CPU sampling and access-log pattern correlation are
now named, concretely, as what 4.6 requires and 4.2 does not provide —
not implemented, not guessed at, until a second real case confirms the
shape worth automating.

**4.5 remains `not verified`, and the criterion itself was corrected
before being advanced.** Asked to qualify the reference incident against
all four labels, the owner found three present — technical debt, energy
inefficiency, sustainability anomaly — and the fourth, deployment
misconfiguration, explicitly not pertinent. A criterion reading
"simultaneously as [all four]" that its own reference incident could not
satisfy was a defect in the criterion, not a gap to force closed by
relabelling `--reload` as a deployment misconfiguration it was not judged
to be. `OPS-0004` records the correction: the vocabulary stays closed at
four, a finding cites whichever the evidence supports, and "deployment
misconfiguration" keeps no definition at all rather than one invented to
fill the fourth slot — the same `GOV-P-001` discipline that left
`OPS-0001`'s `S-001`–`S-003` `unknown` rather than guessed.

**What is proven and what is not.** `OPS-0004` proves three definitions
exist, stated by the owner, each anchored to the one case this heritage
has measured. Nothing wires them to a live finding: `RuntimeFinding`
carries no qualification field, and each of the three still-open
definitions needs evidence no current provider collects — a corrections
backlog a fixed issue can be removed from, for technical debt; the "no
incoming request, no active session" absence-of-benefit evidence the
reference incident had, for energy inefficiency; a real temperature
reading correlated to the CPU reading, for sustainability anomaly. One
case is a policy, not yet a pattern worth automating — `ARC-P-006` holds
here as it does for 4.1's threshold and 4.3's single flag.

**4.8 remains `not verified`, and the arithmetic it needs now exists,
separately from a live reading.** The criterion, literally: "before/after
verification measures a CPU reduction ≥ 95 %."
`CpuReductionMeasurement` (`src/aistack/contracts/cpu_reduction.py`) refuses
construction unless both the before- and after-reading carry their own
observation reference — the same discipline `CorrelatedFinding` already
holds each of its three readings to — and exposes the reduction as a
computed percentage against a declared threshold, defaulting to the 95 %
this criterion names.
`test_the_reference_incidents_upper_bound_meets_the_threshold` applies it
to the numbers already in this repository: 58 % (this reference incident's
own upper bound) to 0.32 % (`docker-compose.selection-ui.yml`'s own
comment, measured after two minutes of inactivity) is 99.4 %, and the
class agrees.

**What keeps this `not verified` rather than satisfied.** The 0.32 %
figure the arithmetic above trusts is a comment in a compose file, written
once by a human, not a reading `aistack` took itself — the same gap `4.1`
closed for "undeclared," not yet closed here for "after." A live
`collect_cpu_readings()` sweep confirming `aistack-selection-ui` still
reads near 0.32 % today, cited as its own observation reference in place
of the compose comment, is what turns this from arithmetic proven correct
into a verification proven current — the same standard `4.7` held itself
to before citing `OPS-0003` as more than a register nobody had exercised
end to end.

---

**Suite state: 22 criteria — 13 satisfied, 0 failing, 9 not verified. Two
scenarios satisfied in full: VS-1 (four of four) and VS-3 (three of three) —
§ 7, a scenario is satisfied only when every one of its criteria holds.**

---

## 10. Out of Scope

- Performance benchmarking of AIStack itself.
- Validation of third-party runtimes.
- The Adaptive Resource Scheduler and the Knowledge Time Machine — roadmap items,
  not acceptance criteria. They remain in `99-meta`.
- Any criterion requiring a human to interpret the result.

---

## 11. Future Evolution

- Scenarios are added when a capability claims to be demonstrable, never before.
- Criteria migrate from `not verified` to `satisfied` only through an executed
  verification, recorded with its date.
- A criterion that becomes automated should be executed by the same loop as the
  integrity report, so that a regression is visible per commit.

---

## 12. Related Knowledge Artifacts

- STD-0200 — Specification Standard
- FDN-0003 — Constitution (Article 5, Explainability; Article 12, Uncertainty)
- FDN-0007 — Governed Engineering Cycle
- FDN-0008 — Self-Application Principle
- FDN-0012 — OPS-P-004 *Observe before acting*, ENG-P-005 *Validate every
  architectural step independently*

---

## 13. Related Architecture Decisions

- ADR-0008 — Evidence-Driven Observation Architecture (admitted into the governed
  heritage on 2026-08-21; it was in `docs/incoming/` when this suite was written)
- ADR-0005 — Context Bundle Engine
- ADR-0007 — Context Bundle Transfer

---

## 14. References

None external. Every criterion derives from artifacts of the AIStack Governed
Heritage.
