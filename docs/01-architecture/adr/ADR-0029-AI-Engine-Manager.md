---
artifact:
  id: ADR-0029
  title: AI-Engine Manager
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C1
  confidence: Declared
  version: 0.14
  status: Accepted
  owner: Architecture
  created: 2026-11-20
  updated: 2026-11-21

relations:
  references:
    - ADR-0014
    - ADR-0019
    - ADR-0027
    - ADR-0028
---

# ADR-0029 — AI-Engine Manager

## Status

Accepted, 2026-11-21, by the owner, with the answers to the open points below. Proposed on 2026-11-20; scope and three
choices decided with the owner on 2026-11-19 and 2026-11-20 (§ 2, § 4, § 6, and the order of the slices). The record (M1), the policy file (M2), the routing by policy (M3), the ChatGPT and Claude engines (M3b) the choice of engine by kind of request (M3c) and the page of § 8 (M4) exist in code. On 2026-11-21 the owner asked that the policy choose the best engine for the kind of request, internal or external, and say why (§ 10).

## Context

*Read in the code, 2026-11-20.*

AIStack asks a model in four places, and each one has its own route,
written in `troubleshooting/guide.py`:

- **The troubleshooting assistant** (`ask_ai_runtime`) asks Google
  Gemini first when its key is set: the question and its facts then
  leave the local network (the page says so before the click). The
  declared local engines answer when Gemini is not set or is silent.
- **The Security page** (`ADR-0028` T4b), **the watch** (`ai.reason`)
  and **the comparison** (`ai.compare`) ask the declared local engines
  only (`ask_local`): Ollama (`qwen2.5:7b`), then Olala, started on
  demand by an actuator (`ADR-0028` T4d).

What is missing:

- **No policy.** Which engine answers is a line of code, not a decision
  the owner can read, change or audit. Nothing says what may leave the
  network except the order in which two functions call their engines.
- **No trace.** Nothing records who asked, which engine answered, how
  long it took, or what was set aside. The only record is the answer
  itself, in `ai-reasoning/`, and only for the pages that keep one.
- **A hole beside it.** Home Assistant talks to Ollama directly, without
  passing through AIStack. This ADR does not close it (§ 9).

Three facts frame the risk:

- **The data that leaves is the data of the machines.** What Gemini
  receives from the assistant is names of files, services and hosts:
  it describes the owner's network. That is not personal data in the
  usual sense, and it is not nothing.
- **A small local model is sometimes not enough.** Olala and
  `qwen2.5:7b` break their own rules from time to time (`ADR-0028`
  T4c): a better engine is tempting, and it is outside.
- **A fallback is a decision.** "The local engine is silent, so ask the
  external one" is the most natural line to write and the one that
  sends data out on the day the machine is already in trouble.

## Decision

### 1. One place decides, and it does not replace the engines

The Manager is the one entry point for a question to a model: the
caller says who it is and what it asks; the Manager decides which
engines may be asked, in which order, and records the decision. The
engines (`AIEngine`: Ollama, `openai_chat`, Gemini) and their guards
(`ADR-0028` T4c, T4d) stay as they are. The Manager adds a decision
before them and a record after them.

### 2. Data has a class, declared by the caller

Decided by the owner, 2026-11-20. Two classes:

- `internal_only`: what is asked never leaves the machines the owner
  runs.
- `external_allowed`: what is asked may go to an external engine.

The class belongs to the *use*, not to the text: the Security page, the
assistant, the watch each declare theirs, in a governed file
(`ai_policy.yml`), and the owner is the only one who changes it. The
Manager does not read the text to guess a class; detectors of shapes
(addresses, paths, secrets) are not part of this decision and would be a
later, separate one. **In doubt, `internal_only`**: a caller the file
does not name is internal.

### 3. Engines are internal or external

An engine is *internal* when it runs on the owner's machines (Ollama,
Olala, any `openai_chat` server on the loopback or the LAN) and
*external* when it does not (Gemini, ChatGPT, Claude). Built in M2, the rule is read from
where the engine answers, not from a name the owner must keep up to
date: a loopback, private (LAN) or link-local address is internal, a host
name the owner lists in `internal_hosts` is internal, and anything else
(a public address, a host name not listed) is external, the cautious
side. Gemini, ChatGPT and Claude have no address of their own to read and are always external. They are declared in `ai_runtime.yml` (`gemini:`, `openai:`, `anthropic:`: a model and the name of the environment variable holding the key, never the key) and asked only when the key is set.

### 4. The routing rule

Decided by the owner, 2026-11-20. For a call of class C:

- an `internal_only` call reaches internal engines only, in the order
  declared;
- an `external_allowed` call may reach any engine; which one is asked
  first is § 10's business (until then: Gemini, ChatGPT, Claude, then
  the local engines, the first that answers);
- **a call never crosses its class to find an answer.** When every
  engine its class allows is silent or set aside, the answer says so
  and the hand-written text stays: the Manager does not ask an external
  engine because the internal ones failed.

The shipped class of the troubleshooting assistant is `internal_only`:
it keeps Gemini only if the owner declares its facts `external_allowed`.

### 5. Personal data and a local engine that is not enough

Decided by the owner, 2026-11-19. If personal data is in play and no
internal engine is capable enough, the internal engine is used anyway
and the limit is written in the record (§ 6): the data never leaves,
the answer may be weaker, and the record says so.

### 6. Every decision is recorded, never the content

One line per call, in a bounded history: the date, the caller, the
operation, the language, the class, the engines the call was allowed to
reach, the engine that answered (and its kind, internal or external),
the duration, whether anything answered, and the reasons an answer was
set aside (`answer set aside twice, it broke the rules: …`). **Never**
the question, the answer, the evidence lines, or a name or an address
taken from them. The record is written by a Task (`ADR-0027`'s rule: no
write outside the Runtime), kept for a bounded time, and read by the
page of § 8.

### 7. The user chooses nothing

The page keeps one button. Which engine answers is the declaration's
business, not the reader's. Two things stay honest, as they already
are: the page says where the question goes before the click, and every
answer names the model that gave it. Both now read the policy.

### 8. A page shows what happened

A read-only page lists the engines and their state (Ollama on the GPU or
the CPU, Olala stopped or starting), counts by caller and by engine, the
share of calls that stayed internal, and the last set-asides. It
changes nothing.

### 10. The best engine for the kind of request

Decided by the owner, 2026-11-21: the policy chooses the best engine for
the kind of request, from the question asked and the problem to treat,
among internal and external engines alike; among the external ones it
chooses between ChatGPT, Gemini and Claude; and it says why.

Choices made with the owner the same day:

- **The kind is declared, not detected.** A kind (a diagnosis, an
  explanation, a recommendation, a comparison, and so on) is named in
  `ai_policy.yml` (`kinds:`) for each operation, or for one operation of
  one caller (`troubleshooting.reason`). Refining it by the domain of
  the finding (disk, network, security…), a label AIStack's own
  qualification gives and not text from the question, is not built: see
  the open points. The Manager does not read the question to class it,
  and no model decides (§ 9 stands).
- **The choice reads a declared table** (`preferences:`), kind by engine:
  an ordered list of engines for each kind, each with the reason the owner
  gives for it
  ("long reasoning over several facts", "short and fast", "keeps French
  tutoiement"). The comparison of engines (`ai.compare`) may later
  correct the table; it does not replace it. A reason is a plain text or a
  mapping of a language code to its text (the reference language, `fr`, being
  required): the journal records one text (the English one), the pages say it in
  their own language (`ai_runtime/reasons.py`), and a copy of the file written before
  the translation is read in French too, its texts being looked up in the shipped
  file.
- **The class stays a ceiling.** The best engine is chosen among those
  the caller's class allows (§ 4): an `internal_only` caller never sees
  ChatGPT, Gemini or Claude however well they would do. A caller that
  wants them declares itself `external_allowed`.
- **The rule.** Among the engines the class allows, declared, with their
  key set and not shut off, the first of the kind's list is asked; when
  it is silent or its answer is set aside, the next of the list, never an
  engine outside the class (§ 4). A kind with no list falls back to the
  order declared. An engine is a name (`gemini`, `openai`, `anthropic`),
`local` (the local engines in the order declared) or the label or model
of one local engine, so an internal engine can be ranked above an
external one for a kind.

**Why is recorded with every choice**, in `route`, from declarations
only: the kind, the engine chosen, the reason the table gives for it, and
what was left out and why. A line reads
`external_allowed; kind=diagnosis; chose gemini: fast; silent: anthropic
(Claude refused the request with status 529); passed over: openai (key
not set)`. Never the content. The
page of § 8 shows it, and the answer already names the model that gave
it (§ 7).

### 9. What this ADR leaves out

- **Other applications** (Home Assistant and any other client): they
  reach Ollama without the Manager. A portal for them, behind the OIDC
  provider the owner uses (Pocket ID), is a later decision. Who may read
  the page of § 8 follows `ADR-0014` (profiles and rights).
- **Choosing an engine by what the text says**, and any choice made by a
  model: the Manager decides from files, deterministically.
- **Cost and quotas** of an external engine. The owner sets a spending limit on each provider's account; a guard of the Manager's own may come later.
- **A further external engine** (Olala on a hosted service, for
  instance): it would be declared external and follow § 3, § 4 and § 10
  unchanged.

### 11. Each card of the console says whether its screen uses AI engines

Decided by the owner, 2026-11-21. Every card of AIStack's own in `console_links.yml` declares `ai_callers`:
the uses of a model of `ai_policy.yml` its screen reaches (`[]` for a
screen that asks no engine). The console writes under the description,
from those uses and the policy: *asks no AI engine*, *local engines
only, nothing leaves your machines* (every use `internal_only`), or
*local, or at an outside provider when your policy allows it* (any use
`external_allowed`). The line follows the policy, so it stays true when
the owner changes a class. It is written for the language of the page.
The `ai` sentence, where a card has one, still says what the AI does
there. A card of the owner's own without `ai_callers` says nothing of
AI: the console does not know what it reaches. A copy of the file made
before `ai_callers` takes them from the shipped card of the same screen
(`ADR-0017` § 1).

### 12. A page for everyone: "Poser une question"

Anyone signed in on the local network (not only an administrator) asks a question in their own words
on `/ask/`. The caller is `portal.chat`, `external_allowed` as shipped, **and every question is screened
for personal data before any engine is chosen** (§ 5): when the screen finds some, the call is
`internal_only` whatever the class, so the question stays on the machines; when it finds none, the policy
decides as for any caller, an outside engine being asked only when declared with its key set. The screen is
`portal/personal_data.py`: shapes recognised by their form (e-mail address, telephone number, IBAN and card
number checked by their keys, social security number, postal address, IP or MAC address, secret such as a
key or a private key, date of birth) and the words of `portal/definitions/personal_data.yml` that point at
a private matter (identity, secret, family, health, money, legal, biometric, belief, work, place — the
families that rgpd.com lists among personal data — and `names`, the first names of the owner's house, empty as
shipped), which the owner can extend. A word that is also an
everyday word of a technical question (a speaker, a voltage) is written in the first person or left out. In doubt the
question stays inside: a question kept inside by mistake costs a weaker answer, one that leaves by mistake
cannot be called back. A first name alone cannot be told from another word, except those the owner lists under `names`: the page
says so before the click. The screen returns kinds, never text: the page shows "e-mail address, family", the route of the
journal says `personal data: email, family`, and no word of the question is kept anywhere.

The operation is `ask`, of kind `question` (a row in `kinds:` and a list in `preferences:`), so the policy
chooses the engine as for any other call. The answer names the engine that gave it, the reason the policy
gives for it, the personal data found (or none) and whether the question stayed on the machines. What is
typed is held in memory for the length of the exchange (half an hour at most, one question at a time per
person) and written nowhere. The page is reached from a card of the console and from the Homepage dashboard.

## Consequences

- The owner can read, in one file, what may leave the network and which
  use may send it.
- The troubleshooting assistant stops calling Gemini until the owner
  declares otherwise: a change of behaviour, made on purpose and
  recorded.
- A day when every internal engine is silent gives an honest "no
  answer", not an answer from somewhere else.
- The record shows, before any rule is tightened, what the console
  really asks and of whom.

## Implementation state

M1 to M4 and M3b, M3c are built; the rest is not. Planned slices (each its own patch, tested before
delivery):

| Slice | State |
|---|---|
| M0 — This ADR | done — 2026-11-21, accepted by the owner (proposed 2026-11-20) |
| M1 — The record: each call carries the name of its caller; one line per call in `ai-calls.jsonl`, without content; routing unchanged | done, 2026-11-20 (0091): callers `troubleshooting`, `security.page`, `vigil.reason`, `ai.compare`; 90 days kept; `AIRuntimeAnswer.external` marks a question that went to an external engine. Written by the process that asks (the web service, the watch, the comparison), as state a service keeps for itself in the GHE audit; § 6 said "by a Task", which does not fit the web service, so the rule is read as "declared in the audit" |
| M2 — Classes and policy: `ai_policy.yml` (caller to class, `internal_hosts`, internal by default); the record says, per call, its class and whether a routing by the policy would have changed it | done, 2026-11-21 (0092): shipped `ai_policy.yml` (four callers, all `internal_only`), loader and `AIPolicy` in `ai_runtime/policy.py`, `policy_class` and `policy_differs` in each line of `ai-calls.jsonl`. The page's destination (`ai_destination()`) is **not** changed: it must keep telling where the question really goes, and nothing routes by the policy before M3 |
| M3 — Routing by policy: `ask_managed` replaces the direct calls; Gemini only when the caller's class allows it | done, 2026-11-21 (0093): `ask_managed(caller, …)` in `troubleshooting/guide.py` serves the assistant, the Security page and the watch; an `external_allowed` caller is asked as before (Gemini first when its key is set), an `internal_only` one reaches internal engines only, never crosses its class when they are silent, and says so. `ai_destination()` follows the policy. `ai.compare` refuses an engine outside. Each answer carries `route`, kept in the journal (`internal_only; not asked: gemini`). The shipped class of the assistant stays `internal_only`; an installation that keeps Gemini declares `troubleshooting: external_allowed` in its own `ai_policy.yml` |
| M3b — ChatGPT and Claude as external engines beside Gemini: `OpenAIEngine` and `AnthropicEngine` (`ai_runtime/hosted_engines.py`), `openai:` and `anthropic:` in `ai_runtime.yml`, the two keys in Settings (`AISTACK_OPENAI_API_KEY`, `AISTACK_ANTHROPIC_API_KEY`), the page's text before the click for each | done, 2026-11-21 (0094): asked in the order Gemini, ChatGPT, Claude, then local, only when declared and the key is set, and only for an `external_allowed` caller; `route` of an `internal_only` caller lists every outside engine it was kept from. Nothing is declared by default: no behaviour changes until the owner declares a model and sets a key |
| M3c — The best engine for the kind of request (§ 10): kinds per operation, the table kind by engine with its reasons, the rule, `route` and `kind` carrying the why | done, 2026-11-21 (0095): `ai_runtime/choice.py` (`plan`, a pure function of the declarations: the steps best first and what it passed over), `kinds:` and `preferences:` in `ai_policy.yml` (strict loader), `ask_managed` runs the steps and stops at the first answer, `kind` added to the answer and to each line of the journal. Shipped table: a starting point written with the owner (diagnosis and recommendation prefer Claude then ChatGPT then Gemini, explanation prefers Gemini, each ending on the local engines), to be corrected by what `ai.compare` shows. With only Gemini set, behaviour is unchanged. The page's destination names the first outside engine any of the three operations asks |
| M4 — The read-only page of § 8 and its console card, showing the why of § 10 | done, 2026-11-21 (0096): `/ai-engines/` (LAN only, signed in), `ai_runtime/engines_view.py` builds it from the declarations, the keys present (names only) and the journal. Engines with their state (ready, key missing, not declared), where they run and when each last answered or stayed silent; the policy (class per caller, kinds, the table with its reasons); counts by caller, kind and engine, the share that went outside and the calls where a first engine was silent; the latest 30 calls with their route. It asks no engine, so the state is what the declarations and the journal say, not a probe (an Ollama on the GPU or the CPU, an Olala stopped or starting, is not shown: a probe would make the page wait on a slow engine) |
| M4 bis — A line on every card of the console: asks no engine, local only, or outside allowed (§ 11) | done, 2026-11-21 (0098): `ai_callers` per card, `ai_use` worked out from the policy by `console/ai_use.py` |
| M5 — The page for everyone of § 12 | done, 2026-11-21 (0100, 0101): `/ask/` (LAN only, signed in, `USER_ACTION`: any signed-in person, with the session's token), `portal/chat.py`, operation `ask` in `ai_runtime/operations.py` (the matter of a question is an `AIMatter`, a `RuntimeFinding` being one), `portal.chat` in the shipped `ai_policy.yml`, a card with `ai_callers: [portal.chat]` |
| later — A portal for other applications behind the OIDC provider | not started, to be decided |

## Open points, settled on 2026-11-21

- **How long the record is kept: 90 days**, dropped by age; it is already so since M1 (0091). No bound by size: one
  line per call, without content, stays small over 90 days.
- **The list of callers is the policy file.** `ai_policy.yml` names them (`troubleshooting`, `security.page`,
  `vigil.reason`, `ai.compare`, `portal.chat`); a caller it does not know stays internal, as the rule says. A new
  caller is declared there, and in this ADR when it matters.
- **How a caller declares the capability it needs of an engine: postponed.** The table of kinds by engine is enough
  today; it is reopened with the first caller that needs more (images, a long context).
- **Home Assistant through the Manager: no, for now.** It keeps its own path; the question is reopened only if the
  owner asks.
- **The finding's domain as a refinement of the kind, and the shipped table: postponed** until a few weeks of
  comparisons (`ai.compare`) on the owner's own findings show what to change.
- **An engine that answered badly several times in a row, put behind the next one: postponed** until the record
  shows such a case.
