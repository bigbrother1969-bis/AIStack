---
artifact:
  id: OPS-0001
  title: Container Log Signatures
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.2
  status: Draft
  owner: Operations
  created: 2026-08-22
  updated: 2026-09-04

relations:
  references:
    - ADR-0009
    - FDN-0002
    - STD-0300
    - OPS-0003
---

# OPS-0001 — Container Log Signatures

## Purpose

This register declares the rules by which a container's log is interpreted.

FDN-0002 defines a *Knowledge Policy* as "a governed rule defining how
knowledge is evaluated, qualified or interpreted", explicit and versioned.
Each signature below is one. A runtime finding cites the signature that
produced it, which is what STD-0300 § VS-4 criterion 4.7 asks for when it
requires a remediation to name the policy it derives from.

## Provenance

These four rules were written between 2026-07-01 and 2026-07-04 in
`backend/services/docker_service.py`, inside a function called
`analyze_container`, in a repository that was declared nowhere until
2026-08-21. They are what an initial experimenter established: that knowledge
can be recovered from an existing Docker implementation.

They are the owner's operational knowledge, learned from incidents on this
deployment. Verified on 2026-08-22: none of the four patterns appeared
anywhere in the governed heritage — not in the 290 lines of Docker code
spread over eleven files, not in any document.

**The English below is a translation.** The original wording is French and
lives in `analyze_container`, in `aistack-origin`. Where the two diverge, the
French prevails — the same rule the heritage adopted for FDN-MANIFESTO on
2026-08-21. Nothing was added, removed or reinterpreted in the passage from
one to the other.

## How this register is read by a program

The signatures live in one fenced block tagged `signatures`, below. Prose is
free everywhere else in this document; that block is the only place where an
edit can change what a machine does.

The tag is a custom info string rather than `yaml`, deliberately: a document
explaining itself may well contain an illustrative `yaml` block, and a parser
that took the first one would eventually take the wrong one. **Exactly one
`signatures` block belongs in this document.**

That block is parsed at projection by an integrity check, so a malformed
catalogue stops a publication rather than a diagnostic. The same parser reads
it at runtime, on this document — one contract, not two. ADR-0009 § 4 records
the decision and why the stricter alternative was rejected.

## What is not yet decided

**Every `depth` below is 100**, which is what the experimenter read for every
rule without distinguishing them. ADR-0009 § 3.1 makes the window a property
of each signature precisely so that they need not be equal; recording 100
four times transcribes what the code did, and states nothing about what each
rule needs. A `TLS Error` preceding its symptom by two hours would not be
found at this depth, and nothing would say so.

**`applies_to` records what the first real run established, and no
more.** On 2026-08-22 this chain swept 62 containers and produced one
finding: eleven connection refusals in `frigate`, exact in their detection
and empty in their remediation. `frigate` is stopped on purpose on this
deployment — started on demand for Oak-15, shut down after — and those lines
are what an nginx prints while its backend goes away. `S-004` therefore
declares `running`.

The other three declare `any`, which transcribes what the experimenter did:
it applied every rule to whatever container a human had clicked, whatever its
state. Nothing observed says whether that is right for them, and nothing here
pretends otherwise.

**A deeper gap has no field — had no field.** The heritage could not tell
"stopped because broken" from "stopped on purpose", because nothing
declared which containers are expected to run. `applies_to` treats the
symptom; the knowledge that `frigate` is deliberately idle existed in one
person's head.

`OPS-0003`, written 2026-09-04, is that field. It declares `frigate` as
`intermittent`, in the owner's own words, and `ground_findings`
(`src/aistack/runtime/grounding.py`) adds that context to any finding whose
subject `OPS-0003` names — carrying the signature's own interpretation and
remediation forward unchanged, never suppressing them. This signature's own
`applies_to` and `grounding` are unchanged by that: `S-004` still declares
`grounding: unknown`, because the general remediation this signature
presupposes for any subject remains ungrounded. What `OPS-0003` grounds is
the one finding it has a stated fact about, not the rule.

**Every `grounding` below is `unknown`.** The field names the rule that makes
a remediation the right one — not the signature itself, which is the rule for
interpreting. "Check the VPN credentials the container uses" is only
actionable if those credentials have a declared location; "check the target
service, the exposed port and the Docker network" presupposes that a
dependency between two services is declared somewhere. Neither rule exists in
this heritage. Recorded as `unknown` under FDN-0003 Article 12, and countable
as such — the owner's position of 2026-08-22 is that a well-founded and
explainable system is the target, and that some ancillary rules may stand
without an explicit policy.

**Every `confidence` is `Declared`.** They were written from experience, none
has been re-verified by a third party, and no test proves that any of them
fires on the incident it describes. Raising one to `Verified` means
reproducing that incident.

## The signatures

```signatures
artifact: OPS-0001

signatures:

  - identifier: OPS-0001/S-001
    applies_to: ["any"]
    pattern: "AUTH_FAILED"
    case_sensitive: true
    interpretation: "OpenVPN reports an AUTH_FAILED error."
    remediation: "Check the VPN credentials the container uses."
    depth: 100
    confidence: Declared
    grounding: unknown

  - identifier: OPS-0001/S-002
    applies_to: ["any"]
    pattern: "Your credentials might be wrong"
    case_sensitive: true
    interpretation: "Gluetun states explicitly that the credentials may be wrong."
    remediation: "Update the NordVPN / OpenVPN credentials in the Gluetun configuration."
    depth: 100
    confidence: Declared
    grounding: unknown

  - identifier: OPS-0001/S-003
    applies_to: ["any"]
    pattern: "TLS Error"
    case_sensitive: true
    interpretation: "TLS errors are present in the VPN logs."
    remediation: "Check network connectivity, the chosen VPN server, and the certificates."
    depth: 100
    confidence: Declared
    grounding: unknown

  - identifier: OPS-0001/S-004
    applies_to: ["running"]
    pattern: "connection refused"
    case_sensitive: false
    interpretation: "The logs contain connection-refused errors."
    remediation: "Check the target service, the exposed port, and the Docker network."
    depth: 100
    confidence: Declared
    grounding: unknown
```

## A difference the experimenter never declared

`S-004` compares without regard to case; the other three compare the text as
written. In `analyze_container` that difference is `logs.lower()` on one line
out of four, and nothing in the code says whether it was a decision or an
accident.

It became visible only when the rules had to be transcribed into a form that
required them to state it. The contract had no field for it on 2026-08-22
either — `case_sensitive` was added to `Signature` the same day, without a
default, so that no signature can inherit a comparison it never chose.

Whether `S-004` should be the only case-insensitive rule is undecided, and it
is recorded here rather than settled.

## What this register does not do

It does not classify a finding as technical debt, deployment
misconfiguration, energy inefficiency and sustainability anomaly at once, as
STD-0300 § VS-4 criterion 4.5 requires. Inventing that four-term vocabulary
would be authoring governed knowledge, which GOV-P-001 forbids. Criterion 4.5
remains `not verified`.

It does not describe container state — not running, unhealthy, no healthcheck
declared. That is a different observation and a different rule, and the
experimenter kept it in a separate function.
