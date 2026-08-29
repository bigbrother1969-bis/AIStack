---
artifact:
  id: ADR-0009
  title: Runtime Evidence Qualification
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.10
  status: Accepted
  owner: Architecture
  created: 2026-08-22
  updated: 2026-08-29

relations:
  references:
    - ADR-0008
    - STD-0300
    - STD-0102
    - FDN-0011
---

# ADR-0009 — Runtime Evidence Qualification

## Status

Accepted, 2026-08-22.

**Written and accepted the same day, which is an exception to a rule adopted
the day before**, and it is recorded rather than passed over.

That rule — an act binding the heritage is proposed one day and accepted the
next — was adopted on 2026-08-21 after a session in which four C3 artifacts
were revised and one engraved within hours of being proposed. Its purpose
was to stop a decision being fixed minutes after an agent had framed it.

Here the delay was spent on instruction instead of on the calendar. The
decisions rest on seven questions answered by the owner, and the record was
amended twice before acceptance — both times because reading the heritage
contradicted the way the agent had posed the question:

- the first draft claimed no policy justified the remediations. FDN-0002
  defines *Knowledge Policy*, and a log signature matches that definition
  exactly. The question had been asked without reading the glossary entry
  that answered it. What survives of the gap is narrower, and is recorded in
  § 3.1 as `grounding`;
- the point that amendment left open — how an individual signature is
  identified — was settled in § 3.2.

A rule whose purpose is met by another means is not a rule that was ignored.
Recording both is what lets a later reader judge that for themselves.

Two revisions this decision carries — `OPS-` in STD-0102, `Operations` in
`KnowledgeDomain` — widen two closed vocabularies and are *not* part of this
acceptance. They are separate acts.

## Context

*This section states the situation as measured on 2026-08-22, the day this
decision was accepted, and is not rewritten as that situation changes. The
container it describes was retired on 2026-08-27 — GOV-0002/OS-012 — and the
tense below is the tense in which the decision was taken.*

A container named `aistack-backend` has been running on this deployment
since before the governed repository existed. Its image was built on
2026-07-01; the repository's first commit is 2026-07-04.

Its source is 361 lines of FastAPI and static JavaScript, held in
`/srv/aistack`, a second git repository that contains this one as a
subdirectory and was declared nowhere until 2026-08-21. Nine navigation
modules are announced, one is implemented; the application itself renders
*"Module prévu, pas encore implémenté"* for the other eight.

**The owner qualified it on 2026-08-22 as an initial experimenter**, whose
purpose was to establish that knowledge can be recovered from an existing
Docker implementation. That qualification is what this ADR acts on: an
experiment that has produced its result is not maintained, it is harvested.

What it established is concentrated in about twenty lines of
`analyze_container`: four log signatures learned from operating this
homelab, each with an interpretation and a remediation.

```python
if "AUTH_FAILED" in logs:                     → OpenVPN credentials
if "Your credentials might be wrong" in logs: → NordVPN / Gluetun credentials
if "TLS Error" in logs:                       → VPN server, certificates, network
if "connection refused" in logs.lower():      → target service, port, Docker network
```

Verified on 2026-08-22: none of these four strings appears anywhere in the
governed heritage — not in the 290 lines of Docker code spread over eleven
files, not in any document. The observation side exists and is better; the
interpretation side does not exist at all.

STD-0300 § VS-4 specifies that interpretation — *Runtime Observation → … →
Explainable Recommendation* — and its nine acceptance criteria are all
recorded as `not verified`. The experimenter is a crude, partial, working
answer to a specification written three days after it.

## Decision

The experimenter's function migrates into AIStack. Its code does not.

### 1. The chain is ADR-0008's chain

Nothing new is invented where ADR-0008 already decided:

| ADR-0008 stage | This migration |
|---|---|
| Reality | the running containers |
| Evidence | `docker logs` output, collected and not interpreted |
| Evidence Normalization | a builder that turns raw output into a typed model |
| Canonical Observation | the model the qualifier consumes |
| Item Qualification | matching against the declared signature catalogue |

`ARC-P-012` cuts the chain at Evidence: the provider collects logs and
concludes nothing. The experimenter does both in one function, which is why
its code does not migrate.

`ARC-P-013` forbids the rest of it: *evaluation consumes canonical knowledge
models, never raw technical output*. `if "AUTH_FAILED" in logs` is substring
matching on an undifferentiated blob. The normalization stage exists to make
each log entry an identified thing a finding can reference.

### 2. Qualification consumes governed knowledge — the inversion

ADR-0008's chain ends in the Governed Heritage: reality becomes knowledge.

This one runs the other way at its last stage. The signature catalogue is
governed knowledge, and the qualifier **reads** it. Evidence is qualified
*against* the heritage rather than *into* it, and the result is an
operational report — disposable under `ENG-P-003`, never a Knowledge Asset.

This is the first time `docs/` becomes an input to execution. Until now the
heritage was written by humans, projected as opaque content, and parsed by
nothing. A document that code reads acquires a machine contract in addition
to its human one, and that contract has to be explicit — which is what
FDN-0011 calls the difference between a contract and a claim.

### 3. A signature is a Knowledge Policy

FDN-0002 already defines the term:

> **Knowledge Policy** — a governed rule defining how knowledge is
> evaluated, qualified or interpreted. Knowledge Policies are explicit and
> versioned.

A log signature is that, word for word: a governed rule defining how an
observation is interpreted. The vocabulary did not have to be invented.

The consequence is structural. **The catalogue is a policy register, not a
configuration file that policies would have to justify.** `STD-0300` § VS-4
criterion 4.7 — *a safe remediation is recommended, citing the policies it
derives from by identifier* — is then satisfied by construction: a finding
cites the signature that produced it. That is traceability, not circularity;
the finding is the output and the signature is the rule.

It follows that **each signature carries its own identifier**, not only the
document. `OPS-0001` names the catalogue; something must name the third
signature inside it.

The four signatures are the owner's operational knowledge, learned from
incidents on this deployment. `GOV-P-001` forbids the AI from authoring
them, extending them, or rewording them.

Coding them into a Python module would reproduce, on the day it was
described, the defect this heritage spent 2026-08-20 and 2026-08-21
removing: knowledge embedded in code rather than declared.

### 3.1 What a signature declares

| Field | Rule |
|---|---|
| identifier | unique; a finding cites it |
| pattern | what is matched in the evidence |
| case_sensitive | whether the comparison regards case |
| applies_to | the subject states in which the rule means something |
| interpretation | what the match means |
| remediation | what to do about it |
| depth | the log window in which the signature has meaning |
| confidence | `Verified` / `Reviewed` / `Declared` |
| grounding | the policy the *remediation* rests on, or `unknown` |

**`case_sensitive` and `applies_to` were not in this table when the decision
was accepted.** Both were added on 2026-08-22, both because usage revealed a
field the decision had not foreseen, and both without a default so that no
rule inherits a behaviour it never chose.

`case_sensitive` surfaced during transcription: the experimenter compares
three patterns against the log as written and the fourth against
`logs.lower()`. That difference is one line of code and says nothing about
whether it was decided. It only became visible when the rules had to be
written in a form that required them to state it.

`applies_to` surfaced on the first real run. `frigate` produced eleven
connection refusals — exact in detection, empty in remediation — because it
is stopped on purpose on this deployment and those lines are what an nginx
prints while its backend goes away. A rule that only means something on a
running container has to be able to say so. `any` is the declared word for
every state and may not be mixed with others.

A third field was added outside this table, on `LogEntry`: the timestamp
`docker logs --timestamps` supplies, carried separately from the text so no
signature compares against a prefix the container never printed.

**`depth` is a property of the signature, not a parameter of the call.** The
experimenter reads the last hundred lines for every rule. A signature whose
useful window is longer would never fire, and nothing would say so — the
system could not tell *absent* from *out of range*. Collection reads once at
the deepest declared window; each signature evaluates its own.

**`grounding` is mandatory and may be `unknown`.** It is not the policy the
signature *is* — that is the signature itself — but the rule that makes its
remediation the right one. *"Check the VPN credentials used by the
container"* is only actionable if those credentials have a declared
location; *"check the target service, port and Docker network"* presupposes
that a dependency between two services is declared somewhere. Neither rule
exists in this heritage, measured 2026-08-28 across every governed artifact.

The owner's position, recorded 2026-08-22: **ideally every signature is
grounded, and a system that is well-founded and explainable is the target;
some ancillary rules may stand without an explicit policy.** Article 12 of
FDN-0003 gives that its form — the field is required, its absence is
declared rather than silent, and the number of ungrounded signatures becomes
a measurable property of the catalogue instead of an impression.

The four initial signatures declare `confidence: Declared`. They were
written from experience, none has been re-verified by a third party, and no
test proves that any of them fires on the incident it describes. Raising one
to `Verified` means reproducing that incident.

### 3.2 A signature exists inside its catalogue

A signature is identified by a fragment of its catalogue's identifier:

```
OPS-0001/S-001 … OPS-0001/S-004
```

**No third identifier convention is created.** The heritage already carries
two — `OPS-0001` for artifacts, `OPS-P-001` for principles — and yesterday
cost a day to make those two unambiguous. A signature is not a governed
object citable from anywhere; it exists inside the catalogue that declares
it, and its identifier says exactly that.

`S-` rather than a bare number, so that `OPS-0001/003` can never be read as
a numbered item of the kind principles are. A slash rather than `#`, because
the catalogue is written as a YAML block and `#` is that language's comment
character — an identifier that needs quoting to survive is a trap left for
later.

`ARC-P-006` is invoked here with its cost known rather than as a
formula. Should a second catalogue appear — Linux, network, storage — and
should a signature need citing from outside its own, promoting these
fragments to first-class identifiers would mean rewriting the citations
carried by findings already produced. Findings are disposable reports under
`ENG-P-003`. Nothing durable depends on this choice, which is what makes
deferring it legitimate rather than merely convenient.

### 4. One parser, two call sites

The catalogue is written as a delimited structured block inside the document
body. Prose stays free everywhere else; the one place where an edit can
break execution is visible as a block.

That block is parsed **at projection**, by a blocking integrity check. A
malformed catalogue stops a publication, exactly as the eight existing
checks do. The same parser is reused at runtime, on the document, so there
is one contract and not two, and diagnosing a container does not require a
regenerated bundle.

The alternative — the qualifier consuming only the published bundle — is a
stricter reading of `ARC-P-013` and was rejected on use: it would make
`export_project_sources.py` a precondition of every diagnostic.

### 5. Identifiers

The catalogue takes a new prefix, `OPS-`, and STD-0102's prefix table gains
it. `KnowledgeDomain` gains `Operations`.

The heritage has carried Operations principles since July — `OPS-P-001` to
`OPS-P-004` — while the code's domain vocabulary had six values and not that
one. An artifact declaring `domain: Operations` would have been normalized to
`unknown`. The domain was missing from the implementation, not from the
knowledge.

### 6. Scope: iso-usage on capability, not on defects

Everything the experimenter let a person do remains doable. Its
measured usage is three interactions: list containers with a state icon,
request a global diagnostic, analyse one container's logs. Two of its routes
— `/{name}/logs` and `/api/ollama/models` — have no caller in its own
interface and are not usage.

Two behaviours were to be corrected rather than reproduced:

- the state icon computes `health.get("Status", "healthy")`, so **a container
  with no healthcheck is displayed as healthy**. Most containers on this
  deployment declare none. Article 12 of FDN-0003 requires three states:
  healthy, unhealthy, undeclared;
- the global diagnostic renders `JSON.stringify(data, null, 2)` in a `<pre>`.
  The capability is kept; that rendering is not a view.

**Neither was performed, and this section said otherwise for five days.**
Until 2026-08-27 the sentence above read *are corrected*, in the present, of
work nobody had done. Measured 2026-08-27: nothing computes three health
states — `DockerRuntimeCatalogBuilder` carries Docker's raw `state` and
`status`, and no type in the package names *undeclared*.

The second correction is discharged rather than owed: the `<pre>` it applied
to belonged to the experimenter, which was retired on 2026-08-27, and a
rendering that no longer exists does not need replacing.

**The first is owed.** It is a correction this C2 decision announced against
FDN-0003 Article 12, and it stands undone whether or not anything displays
it — the wrong icon left with the experimenter, and the right one was never
built.

Decided 2026-08-27 by the owner: **retract first, implement second.** The
paragraph above is the retraction. What follows is the implementation, made
the same day.

#### The health vocabulary is four states, and the fourth is a separate act

`ContainerHealth` and `health_of` derive health from what `docker ps`
publishes — a parenthetical inside `Status`, since Docker exposes no field for
it — and the runtime catalogue carries the result beside the sentence it came
from. **A missing verdict yields `undeclared`.** That is the correction: the
experimenter's `health.get("Status", "healthy")` replaced a missing verdict
with a verdict, which is what Article 12 forbids in as many words.

**The size of that defect was measured before the fix, on the reference
deployment, 2026-08-27:**

| What the runtime declares | Containers |
|---|---|
| nothing — no healthcheck | 44 |
| `healthy` | 17 |
| `unhealthy` | 0 |
| `health: starting` | 0 |

Seventy-two per cent of the deployment was displayed as sound on no evidence.
This section said *most containers on this deployment declare none*; the
number is 44 of 61.

**A fourth state was added, and § *Status* of this record is why it is stated
rather than done.** Widening a closed vocabulary is a separate act — this
decision says so of `OPS-` and `Operations` in its own acceptance. The three
names above have no cell for a container whose healthcheck is declared and
whose verdict has not returned. `undeclared` would deny a healthcheck that
exists; `unhealthy` would state a verdict nobody reached. Both are the
original defect, pointed differently.

**Decided 2026-08-27 by the owner**, on the measurement above, which found
none of it. Zero is an instant and not an absence: the state is transitory by
construction, and each of the seventeen passes through it on every restart for
the length of its `--start-period`. Without the fourth member, the only moment
a sound container is mislabelled is the moment it is watched most closely —
just after someone restarted it.

One behaviour is added, because VS-4 criterion 4.1 asks for detection
*without being pointed at a service*: the qualifier evaluates every
container, where the experimenter requires a container name.

**The web surface is abandoned. Decided 2026-08-27 by the owner.**

It was to follow the pattern the repository already established:
`selection_ui/`, 331 lines at the repository root outside `src/`, importing
the governed library and shipping as its own digest-pinned image. That
pattern stands and is unaffected; nothing is built on it here.

The reading that permits the abandonment is this section's own title —
*iso-usage on capability*, not on surface — and it is the same reading that
permitted retiring `aistack-backend` without the replacement. The three
measured interactions are reachable from the CLI, and the table in § *What the
retirement delivered* names which command replaces which. What is lost is the
interaction and not the capability, and that interaction had one user.

**This is an abandonment, not a deferral.** The row in the implementation
table reads *abandoned* with a date, where it read *not built, and not a
blocker* for five days while nothing surfaced it (GOV-0002/OS-035). The same
distinction closed GOV-0002/OS-034 on 2026-08-27: a migration announced in a
docstring, measured to have no caller, and ended rather than left standing.

### 7. What a running AIStack knows, and what it does not

Section 2 makes `docs/` an input to execution. That has a boundary, and two
questions found it on 2026-08-22 during the first real runs. Both were
qualified by the owner on 2026-08-23 and are written here rather than left in
the register.

#### 7.1 An installed AIStack is a different subject from a governed one

`OPS-0001` declares the signatures and `runtime_diagnose` resolves them from
the repository root. The wheel contains `aistack/` and nothing else —
verified 2026-08-22 by building it and reading its contents. An installed
AIStack therefore fails with an explicit message and must be given
`--catalogue`.

**That is the decision, not a defect.** A governed AIStack requires the
repository. An installed one is an executable without a heritage, and it is
allowed to be: what it may not do is pretend to have one.

`docs/` is not shipped in the wheel. Doing so would make governed knowledge an
artifact of distribution, versioned by the wheel rather than by its Single
Point Of Truth, and would put two copies of it in the world — which FDN-P-005
forbids. `--catalogue` stays optional and the failure stays loud, because a
tool that silently qualified evidence against no catalogue would report a
clean deployment on an empty rulebook.

Of the three readings the register laid out, this was recorded as the most
inconvenient. It was chosen for the reason it was inconvenient
(GOV-0002/OS-014).

#### 7.2 The expected state of a deployment is not declared here

First real sweep, 2026-08-22: 62 containers, one finding, eleven connection
refusals inside `frigate`. `frigate` is stopped on purpose on that
deployment — started on demand, shut down after — and those lines are what an
nginx prints while its backend goes away.

`Signature.applies_to` was added the same day and treats the symptom: a rule
can state that it means something only on a running container. **It does not
close the gap**, and it is deliberately a treatment of the symptom. The
heritage cannot tell *stopped because broken* from *stopped on purpose*,
because nothing states which containers a deployment expects to be running.

That statement is not written here and will not be. **This repository
describes a product; the set of containers one host expects describes that
host**, and declaring it here would make every other installation contradict
it. The gap is real and is now outside this repository's scope rather than
pending inside it (GOV-0002/OS-015).

The same boundary was applied twice more on 2026-08-27, and held both times:
the machine that publishes this repository to the public internet is not
named by the heritage, and OPS-0002 states the publication procedure in roles
rather than machines.

## Consequences

Positive:

- four signatures stop being a side effect of one function and become
  governed, owned, versioned knowledge;
- `STD-0300` § VS-4 criteria 4.6, 4.7 and 4.9 become structurally reachable:
  evidence reference and cited policy are fields of the finding, not
  intentions;
- the experimenter can be retired, and what it established survives it.

- the heritage gains its first policy register. Principles have had one
  since July; Knowledge Policies were defined in FDN-0002 and lived nowhere.

Negative:

- `docs/` enters the execution chain. A governed document now has readers
  that are not human, and editing one can break a diagnostic;
- a signature cannot be cited from outside its catalogue. That is the
  decision of § 3.2 and not an oversight; it is what keeps the heritage at
  two identifier conventions instead of three;
- a new prefix and a new domain value widen two closed vocabularies;
- `IntegrityFinding` cannot be reused. Its contract states *"It proposes no
  remediation"*, and VS-4 requires one. A second finding type is introduced —
  not for symmetry, but because the two differ in what they are about and in
  whether they recommend.

## Implementation state

The order is the one `ARC-P-005` prescribes: contracts, then the catalogue
declared by its owner, then collection, normalization, qualification, a CLI,
and last the web surface.

**As of 2026-08-22, at `47bb2d9`**, everything but the last step is done, and
the chain has run against the reference deployment: 62 containers examined,
none unobserved.

| Step | State |
|---|---|
| Contracts — `RuntimeObservation`, `Signature`, `RuntimeFinding` | done — 2026-08-22 |
| `OPS-0001`, the catalogue declared by its owner | done — 2026-08-22 |
| Collection — `DockerProvider.collect_logs` | done — 2026-08-22 |
| Normalization — `normalize_log_evidence` | done — 2026-08-22 |
| Qualification — `qualify` | done — 2026-08-22 |
| CLI — `aistack.cli.runtime_diagnose` | done — 2026-08-22 |
| Web surface — `runtime_ui/` | **abandoned — 2026-08-27** — see § 6 |
| Retirement of `aistack-backend` | done — 2026-08-27 |
| Health qualification — `ContainerHealth`, four states | done — 2026-08-27 |

*This section previously read "Nothing is implemented", which was true when
it was written on 2026-08-21 and false the same evening. It is the fifth
sentence of that kind found on 2026-08-22, and the first found after
STD-0100 v2.3 made the rule explicit — an assertion about the code carries
the date it was measured. Recorded rather than quietly rewritten, per
GOV-0002/OS-017.*

### What the retirement delivered, and what it did not

`aistack-backend` was retired on 2026-08-27 **without the web surface**, and
the reading that permits it is this section's own title: *iso-usage on
capability*, not on surface. The three measured interactions are doable:

| Interaction | Replacement |
|---|---|
| request a global diagnostic | `python3 -m aistack.cli.runtime_diagnose` |
| analyse one container's logs | the same command, with the container named |
| list containers with a state icon | `docker_catalog`, which carries each container's `state` and `status` — **and which could not run when this table was written** |

**The third replacement was offered by a command that raised on its second
line.** Measured 2026-08-29: `docker_catalog` had carried
`ctx.providers.get("docker")` — an attribute `Kernel` does not carry — since
`f685f97` on 2026-07-20, which is before this table was written on 2026-08-27.
GOV-0002/OS-044, repaired the same day. *The retirement of `aistack-backend`
was therefore justified in part by a replacement nobody had run. What made that
possible is that the replacement was named rather than executed — the same
distinction ADR-0008 § *The Knowledge Dimension* had to correct.*

**The third is also a capability and not the correction this section promised.**
§ 6 says the experimenter's state icon computes
`health.get("Status", "healthy")`, so a container with no healthcheck reads
as healthy, and that FDN-0003 Article 12 requires three states — healthy,
unhealthy, undeclared. Measured 2026-08-27: **nothing implements those three
states.** The catalogue carries Docker's raw `state` and `status`; the
correction was decided and never built.

So the retirement discharged the exposure and left two things undone: the web
surface, and the corrected qualification. Both were recorded as
GOV-0002/OS-035 rather than left implicit in a table cell reading *not
started*, which is how they survived from 2026-08-22 to 2026-08-27.

**Both were qualified by the owner on 2026-08-27, and both were discharged the
same day.** The web surface is abandoned (§ 6). The corrected qualification
was retracted first and then built — `ContainerHealth`, four states, § 6 —
and the row above says `done` where the register can now read it.

*The order was deliberate and is the point of the pair: the retraction was
true the moment it was written, the implementation was not, and separating
them is what stopped an accepted decision from claiming a correction for a
sixth day.*

The exposure is why the order was inverted. `aistack-backend` answered an
unauthenticated API while holding a writable Docker socket — root on the
host — and GOV-0002/OS-012 had carried that since 2026-08-21, mitigated on
the network and unchanged in itself. A surface that has not been built is a
smaller thing than a door that is open.

Three fields the accepted decision did not foresee were added during
implementation: `Signature.case_sensitive`, `Signature.applies_to` and
`LogEntry.timestamp`. Each was revealed by usage — the first by
transcription, the second by the first real run, the third by a finding whose
age nobody could state. § 3.1 records all three and why each arrived, so that
a reader comparing the decision to the result knows the difference was
deliberate.

## Related Artifacts

- `ADR-0008` — Evidence-Driven Observation Architecture, whose chain this
  applies and whose last stage this inverts
- `STD-0300` — Official Validation Suite, § VS-4
- `STD-0102` — Naming Conventions, which this revises
- `FDN-0011` — Contract-Based Engineering
