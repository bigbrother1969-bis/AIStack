---
artifact:
  id: ADR-0010
  title: User Interface Localization
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.3
  status: Accepted
  owner: Architecture
  created: 2026-09-27
  updated: 2026-10-05

relations:
  references:
    - FDN-0003
    - ADR-0001
    - STD-0100
---

# ADR-0010 — User Interface Localization

## Status

Accepted, 2026-10-05, by the owner — at the 1.9 cadrage, after the
decisions below had run on GIGABYTE since 1.2.

Proposed, 2026-09-27.

Written the day the owner took the decisions it records, and left
`Proposed` rather than accepted the same day — the rule adopted on
2026-08-21 (an act binding the heritage is proposed one day and accepted
the next; ADR-0009 § Status records the one exception taken so far). The
decisions below are the owner's; what awaits acceptance is this record of
them.

## Implementation state

| Step | State |
|---|---|
| § 1 — catalogs, `languages.yml`, `Translator` | done — 2026-09-27 (`507fe82`) |
| § 2 — the reference checked by the suite | done — 2026-09-27; since 2026-10-05 the suite also keeps every catalog and the manual free of AIStack version numbers (the owner's rule: a page never says "in 1.x") |
| § 3 — `?lang=`, then the cookie, then the reference | done — 2026-09-27 |
| § 4 — the interface translated, what it displays not; findings translated by catalog | done — 2026-09-27; findings 2026-10-03 |
| § 5 — the console becomes an application | done — 2026-09-27 (`0f37934`); its standard-library server was replaced by the single web application on 2026-10-03 (`ADR-0012`), which keeps §§ 1–4 |

## Context

*Measured on 2026-09-27, at commit `bcee126`.*

Every screen AIStack serves was written in French and in French only:
eleven Jinja templates across four mini-apps (`selection_ui`,
`priority_ui`, `network_discovery_ui`, `troubleshooting_assistant_ui`),
three renderers producing static pages (`console.html`,
`architecture.html`, `health.html`), and the `app.py` of each mini-app,
where error and status sentences are built. Every one declares
`<html lang="fr">`. The governed heritage itself is written in English;
the interface is the only part of AIStack that addresses its user, and it
addressed them in one language with no way to choose another.

The console was a static file (`console.html`) served by the standard
library's `http.server` on port 8183 (`run_console.sh`), reached from the
public internet through the owner's reverse proxy at
`aistack.persiaut-family.fr`, while each mini-app answers on its own port
of `GIGABYTE`, on the LAN only. A static file server can carry no
preference, and a browser never shares a cookie between two host names —
the public console and a mini-app on `GIGABYTE:818x` are two hosts.

The owner's decisions, 2026-09-27
(`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md`):

- the interface language is chosen by the user, in a *Settings* section
  of the console, and the choice extends to every screen of AIStack;
- French is the reference language and English the second, which
  proves the mechanism translates rather than merely wraps French strings;
  further languages are added by catalog;
- until users exist the choice is remembered per browser; it becomes a
  user preference once users and profiles do;
- the language follows the user from the console to each mini-app in
  the link itself, since the cookie cannot;
- every screen is translated in the first version that carries this
  mechanism, not only the console.

## Decision

### 1. Catalogs, not translated copies of each screen

Every word a screen writes comes from `src/aistack/i18n/catalogs/<code>/
<namespace>.yml`, one directory per language and one file per screen. A
screen asks for a message by dotted key through a `Translator`,
conventionally named `t`. No screen carries a sentence of its own.

`src/aistack/i18n/definitions/languages.yml` declares which languages
exist and which one is the reference. Adding a language is one entry
there and one catalog directory; no screen names a language by code.

### 2. The reference language is checked, never assumed

`tests/unit/i18n/test_the_real_catalogs.py` holds, at every suite, that
every language carries exactly the reference's keys with the same named
placeholders, that no message is empty, and that every key any screen
asks for exists — including the four mini-apps, whose `app.py` the
governed suite cannot import (decision #9, 2026-08-29) but whose text it
can read. A key missing at runtime from a non-reference language falls
back to the reference; a key missing from the reference too raises,
because a screen asking for a message nobody wrote is a defect to state,
not to render as an empty string (FDN-0003 Article 12).

### 3. One request, one language

A request is served in the language it names (`?lang=`), otherwise the
one its browser remembers (cookie `aistack_lang`), otherwise the
reference. A request that names a language sets the cookie. An unknown
code falls through to the next rule rather than raising.
`Accept-Language` is deliberately not consulted: guessing from a
browser's setup would serve English to a French-speaking owner with no
visible cause, where the reference until someone chooses surprises
nobody.

### 4. The interface is translated, what it displays is not — findings excepted since 2026-10-03

Headings, labels, buttons and the sentences a screen writes around its
data are translated. What the screen displays is not: a container's name,
a finding's own interpretation, a declared note, an AI answer, the name a
language gives itself. Those stay in the language they were produced in.
Translating them would put words in the mouth of whoever — or whatever —
produced them.

**Revised 2026-10-03 by the owner, for findings.** Reading the
Troubleshooting Assistant in French, the owner found every finding in
English ("certains messages restent en anglais, alors que la langue
d'affichage devrait être en français") and chose catalog translation
over translation by the AI model or keeping English. A finding's
interpretation and remediation are not words someone else wrote: they
are sentences AIStack's own evaluators compose from a measurement — the
interface's own words, with values in them. So an evaluator now
declares them as catalog keys and values (`aistack.contracts
.finding_message.FindingMessage`, carried by `RuntimeFinding.message`),
and the Health cockpit and the assistant render them in the reader's
language (`aistack.i18n.findings`). The English entries render to
exactly the evaluator's own English text, which `RuntimeFinding` keeps
— it is what the AI Runtime is prompted with and what the reasoning
history records — and the suite holds the two to the same words
(`tests/unit/runtime/conftest.py`). The confidence word follows.

Everything else in the first paragraph stands: a container's name, a
declared note, an AI answer, the codes a finding cites (`OPS-0004/...`)
stay as they were produced. A finding whose evaluator has declared no
message yet is shown in English, as before.

### 5. The console becomes an application

The console's static file server is replaced by a small server
(`aistack.console.server`), still standard library only — the console
never needed FastAPI and still does not, so it keeps running on the
governed interpreter with no dedicated environment. It serves the three
generated pages in the negotiated language, and the *Settings* page where
the language is chosen. The static pages stay generated, one file per
language: the reference language keeps each page's historical name
(`console.html`, `architecture.html`, `health.html`) and its history
stream, and every other language adds `<page>.<code>.html` beside it.

**Revised 2026-10-03 by `ADR-0012`.** The standard-library server is
gone: the console is one router (`aistack.web.console`) of AIStack's
single FastAPI application, after decision #9 was revoked for tests
(`GOV-0002/OS-084`). What this section decided about languages is
unchanged — the same paths, the same negotiation, the same generated
pages — because the router only adapts `aistack.console.routing
.respond`, the pure function the server was built around.

## Consequences

- A new screen, or a new sentence on an existing one, is not finished
  until its words exist in every declared language. The suite refuses it
  otherwise.
- The console links to each mini-app with `?lang=` appended, and each
  mini-app remembers the language for its own host from then on.
- **The AI Runtime's answers now follow the display language too**
  (corrected 2026-09-27, still `Proposed`: this record did not need to
  wait for its own acceptance to be revised). The original design left
  this open on the assumption that the interface language was the only
  thing that could drift; the owner's own real use of the guided
  troubleshooting UI found the model itself does not reliably follow a
  French-only instruction either — the answer came back in English
  regardless of what the prompt asked for, whatever the interface said.
  `reason`/`explain`/`recommend` (`aistack.ai_runtime.operations`) still
  ask the model for `target_language` in the prompt, but a second, fast
  model now translates the answer into it whenever it is not English —
  English needs no enforcement, since the model's own unprompted
  behaviour already tends there. `target_language` is whatever language
  the caller is answering for: the CLI's own unchanged French default,
  or the guided UI's own display language.

## Open Points

- **The quality of AI answers, in each language.** Enforcing the
  *language* an answer comes back in (above) says nothing about how
  good that answer is once translated — that is `R8`
  (`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md`), a prerequisite of `1.4`
  and still unmeasured, and `QUAL-0001`'s own human evaluation is still
  open.
- **No translator configured is a silent pass-through.** Without
  `translator_model:` declared in `ai_runtime.yml`, every answer travels
  exactly as before this record's 2026-09-27 revision — a real,
  reachable answer, just not provably in `target_language`
  (`aistack.contracts.ai_runtime_answer.AIRuntimeAnswer.language`'s own
  docstring names the same gap).
- **Per-user preference.** Moves from the browser to the user's profile
  once users and profiles exist; this record is revised then.
