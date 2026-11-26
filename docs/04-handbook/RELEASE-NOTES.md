---
artifact:
  id: RELEASE-NOTES
  title: Release Notes
  type: Release Notes
  semantic_type: Knowledge Artifact
  domain: Foundation
  criticality: C2
  confidence: Declared
  version: 1.22
  status: Draft
  owner: Foundation
  created: 2026-09-04
  updated: 2026-11-26

relations:
  references:
    - OPS-0002
    - GOV-0002
    - STD-0100
    - GHE-IN-AISTACK
---

# Release Notes

## Purpose

What changed for someone using AIStack, one published version at a time —
in plain language, not in the governance vocabulary the rest of this
heritage uses to talk to itself.

## Scope

One entry per version `pyproject.toml` has ever declared and
`bigbrother1969/aistack-core` has published to Docker Hub, oldest at the
bottom. An entry is written when the version is bumped, per `OPS-0002` §
*Recording what's new* — `GOV-0002/OS-055`. This document does not replace
`docker-compose.yml`, which is where the digest that proves a build lives;
it says what the build was *for*.

---

## 2.3.0 — 2026-11-26

**AIStack now checks, by itself, what a person used to check by hand every morning after a
restart. 2.3 adds the *start-up checks*: a verdict "all well since the last start" in the
health strip, a page that says what is wrong and since when, one short Gotify message at
eight o'clock, and, for each machine, the state of its containers, disks, copies,
certificates and domains. The code judges; the AI only explains. `latest` names this
version.**

### What you may notice

- **An indicator in the health strip.** *Start: all well for 5 h 12*, or *n to watch*,
  *n to fix*, *being checked* during the first minutes, or *not judged* when the facts are
  missing or old: a green that stopped being renewed is never shown. It opens the
  *Start-up checks* screen (local network only): each control, the names behind it, and the
  incidents since the start. A control nobody declared anything for says so; a source that
  did not answer is *not read*, never taken for healthy.
- **The base controls.** The containers that should run, the failed units, the
  file systems that should be mounted, the firewall rules, the virtualisation modules, how
  the previous run ended (a power cut, a hard stop), the UPS, the probes you declare, and
  Uptime Kuma's monitors. The results are read from a small host service,
  `aistack-boot-facts` (facts only, every five minutes, a closed list of read commands).
- **The disks.** Scrutiny's SMART readings (a failure is to fix; a counter that rose in the
  last 30 days, or a disk at 55 °C or more, is to watch, with what to do), the machines
  Beszel watches (down, disk, memory, temperature), the trend of each system disk and of
  the data disks (days before full).
- **Copies and restore tests.** Each copy you declare (a backup folder, the rescue image, the
  snapshots of Timeshift read from its logs) must be younger than the limit you set; the
  restore tests recorded in `pra_tests.yml` must have passed and not be too old.
- **Certificates and domains.** The end date of the certificates your hosts present (or of
  a PEM file) and of the domains you rent (asked of the public registries, at most twice a
  day) is watched: to watch within 21 days, to fix within 7 days or when past. Only the end
  date is read.
- **A morning message.** One Gotify message at 08:00 (hour set in `boot_checks.yml`): for each
  machine, how long all has been well or what is to watch.
- **A history.** The page keeps what changed, machine by machine, and each anomaly says since
  when it has lasted. The journal is bounded and holds names, never a line of a log.
- **Other machines.** A companion machine reports its facts through the collector of
  `ADR-0020`; its controls are judged with the same declaration.
- **The AI explains, never judges.** The AI engine of the house may choose extra controls
  to suggest and explain, in a few lines, an anomaly. That text appears only on the page,
  marked as not verified; it is never sent in Gotify and never changes a verdict.
- **A decision.** `ADR-0032` (start-up checks) describes the choices; it stays *Proposed*
  as long as its last slices are not delivered.

### To do when upgrading

- Set `AISTACK_VERSION=2.3.0` in `.env`, then `docker compose pull && docker compose up -d`.
- **A control nobody declared anything for is *skipped*, not passed.** Run `python -m aistack.cli.boot_check --suggest`
  from the installation folder, read what it prints, and copy what suits you into
  `./config/boot_checks.yml`. A file you made earlier is kept.
- **To see containers, units and file systems of the host**, install the host service once, as
  root (the steps are at the top of `deploy/boot-facts/aistack-boot-facts.service`, and in the
  manual under *Start-up checks*). Without it the controls that need it say *not read*.
- **To watch copies, certificates and domains**, declare them in `boot_checks.yml`
  (`copies`, `certificates`, `domains`) and, for copies, tell the host service where they
  live (`AISTACK_BOOT_COPIES` in its `host.conf`).
- **Scrutiny, Beszel, Uptime Kuma, Gotify:** their addresses and keys are entered in Settings;
  each control that needs one says "not connected" until then.
- The package `cryptography` (reading certificates) is now installed with the image; a
  development checkout needs `pip install -e .` again.

### Not changed

The Cybersecurity Manager, the AI policy and its journal, *Moteurs IA*, the installer, the
sign-in and the restore tests work as in 2.2.2. Your `./config` and your data are kept.

### Known limits

- Nothing here repairs: the checks say, they do not restart or correct.
- A domain whose registry does not publish its end date through RDAP is *not read* until you
  write the date by hand in `boot_checks.yml`.
- The snapshots of Timeshift are read from its logs: a log that does not say "saved
  successfully" does not count.
- A machine Beszel does not follow has no disk trend; a data disk is seen only on the host
  that mounts it.

`pytest -q` — 4376 passed; `mypy` — 675 files; 70 knowledge artifacts,
`blocking: 0   warnings: 0   clean: True`.

---

## 2.2.2 — 2026-11-21

**A patch release: you can list the first names of your house so that a question holding one
stays on your machines, and the page *Usage et empreinte* says when the permanent load is
measured instead of calling it a hypothesis. Two decisions are accepted. `latest` names this
version.**

### What you may notice

- **The first names of the house.** The screen for personal data has a new family, *prénoms
  de la maison*, empty as shipped: AIStack cannot know your names. You write them in your own
  `config/personal_data.yml`, under `names:`, and a question that holds one (*Lukas*, whatever
  the case or the accents) stays on your machines, as for any word of the list. The text above the
  question box no longer says that a first name is never recognised: it says that it is, when
  you listed it.
- **A measured permanent load is called measured.** The page said, whatever the file held,
  «hypothèse déclarée, à mesurer en premier». It now follows the status of the parameter: with
  `status: measured` in your `config/footprint.yml`, it says the load was measured and points to
  the source in the table of parameters; with `declared`, it says what it said before. The file
  shipped with the image still declares 2 / 5 / 10 W: it cannot know your machine.
- **Two decisions are accepted.** `ADR-0029` (the AI-Engine Manager) and `ADR-0030` (usage and
  footprint) are Accepted; their open points are answered or postponed in writing. `ADR-0028`
  (the Cybersecurity Manager) stays Proposed: level 1, the clean point and the purge are not
  built. Nothing in the running application changes because of this.

### To do when upgrading

- Set `AISTACK_VERSION=2.2.2` in `.env`, then `docker compose pull && docker compose up -d`.
- **First names:** a `config/personal_data.yml` made earlier replaces the shipped file and has no
  `names:` yet. Add at the end of it, under `cues:`, a line `  names:` followed by one
  `    - "Prénom"` per name.
- **The permanent load:** a `config/footprint.yml` made earlier replaces the shipped one. Replace its
  `baseline_watts` block by your own measure, with `status: measured` and a `source` that says how you
  measured it (the shipped file explains the three values).

### Not changed

Everything else works as in 2.2.1: the Cybersecurity Manager, the AI policy and its journal,
*Moteurs IA*, the installer, the sign-in, the Dock, the restore tests. Your `./config` and your
data are kept.

### Known limits

- A first name is recognised only if you listed it. A name that is also an everyday word
  (a user name, a product) keeps a question inside: a weaker answer, never a leak.
- The footprint limits stand: the making of the machine and the terminal are declared figures,
  and the permanent load is measured by hand, once, not followed over time.

`pytest -q` — 4047 passed; `mypy` — 651 files; 68 knowledge artifacts,
`blocking: 0   warnings: 0   clean: True`.

---

## 2.2.1 — 2026-11-21

**A patch release: the screen for personal data on the page "Poser une question" knows
the families of personal data that rgpd.com lists, and the reason AIStack gives for the
engine it chose is said in the language of the page. Nothing else changes. `latest`
names this version.**

### What you may notice

- **More words are taken for private.** The health words that 2.2.0 missed are there
  (*malade*, *douleur*, *symptôme*, *fièvre*, *allergie*, *vaccin*, *dossier médical*…),
  and so are more words of money (*fiche de paie*, *mon épargne*…), of justice (*casier
  judiciaire*, *amende*…), of the family (*mon conjoint*, *mes parents*…), of identity
  (*mon passeport*, *mon titre de séjour*…) and of secrets. Four kinds are new, with their
  label in both languages: biometric data, beliefs and origins, work or studies, places and
  movements. A word that is also an everyday word of a technical question (*enceinte* for a
  speaker, *tension* for a voltage) is written in the first person, or left out: «une enceinte
  connectée» still goes where the policy sends an everyday question.
- **The reason is in French on the French page.** «Pourquoi ce moteur» and the table of the
  *Moteurs IA* screen said «stays on your machines: nothing you typed leaves the house»; they
  now say it in the language of the page, and so do the routes of the latest choices. The
  journal keeps the English text, so it reads the same whichever page wrote it. A reason in
  `ai_policy.yml` may be a plain text or a mapping of a language code to its text.
- **A tile for «Poser une question» on Homepage**, added by a script run on the host, not
  by the image: nothing in this version depends on it.

### To do when upgrading

- Set `AISTACK_VERSION=2.2.1` in `.env`, then `docker compose pull && docker compose up -d`.
- **A `config/personal_data.yml` made earlier replaces the shipped file.** Without a change it
  keeps the words of 2.2.0. If you never edited it, copy the shipped one over it (keep a copy
  of yours); if you did, add the words you want to your own.
- A `config/ai_policy.yml` copy needs nothing for the reasons: its English texts are read in
  French from the shipped file. The line `portal.chat: external_allowed` of 2.2.0 is still
  yours to add.

### Not changed

Everything else works as in 2.2.0: the Cybersecurity Manager, the AI policy and its journal,
*Moteurs IA*, *Usage et empreinte*, the installer, the sign-in, the Dock, the restore tests.
Your `./config` and your data are kept.

### Known limits

- The screen cannot recognise a bare first name. In doubt a question stays inside; a
  question that holds none of the words can go outside.
- A technical question that holds a word of the list (*symptôme* of a failure, say) stays on
  your machines: a weaker answer, never a leak.
- The footprint limits of 2.2.0 stand: declared figures to confirm, the permanent load
  dominates the total, the GPU power is read in the web container only.

`pytest -q` — 4044 passed; `mypy` — 651 files; 68 knowledge artifacts,
`blocking: 0   warnings: 0   clean: True`.

---

## 2.2.0 — 2026-11-21

**AIStack learns to watch its own security and to choose which AI answers. 2.2 adds a
read-only Cybersecurity Manager, a second local AI engine started only when needed,
an AI policy that decides what may leave your machines and says so for every call,
a page where anyone signed in can ask a question in their own words, and a page that
counts what the AI calls cost in energy and greenhouse gases. `latest` names this
version.**

### What you may notice

- **Security.** A new console card and screen, *Sécurité*, say what the host exposes
  (listening sockets, ports Docker publishes, the firewall), what the containers may
  do to the host, how old the running images are, which host packages and sensitive
  files changed, how many packets the firewall refused and who tried to get in (counted
  from the host's logs, probes told apart from attempts on your applications). It is
  read-only: nothing is closed, restarted or purged. The vigil tells Gotify what
  deserves it (at once from "to fix", one message a day for "to watch") and has a
  maintenance window for your own work. A local AI engine explains a finding in
  plain words; the commands it suggests only read. `ADR-0028`.
- **The web application no longer holds the Docker socket.** It reads Docker through a
  new service, `docker-proxy`, which listens on the host's loopback only and refuses
  every write. A `docker compose up -d` creates it.
- **A second local AI engine, started when needed.** Besides Ollama, a declared engine of
  another kind (OpenAI-compatible, `ai_runtime.yml` `engines:`) can answer; the first
  that answers wins. One that needs the GPU's memory is started on demand by a small
  host service, `aistack-engine-switch`, and stopped when idle. The answers are held
  to written rules (tutoiement, a calm tone, three read-only commands at most): an
  answer that breaks them is asked again once, then set aside for the next engine. The
  host service also restarts Ollama when it came up on the CPU instead of the GPU.
- **Which AI answers is a policy you can read.** `ai_policy.yml` gives each use of an AI
  (the assistant, the Security page, the vigil, the question page…) a class,
  `internal_only` or `external_allowed`, and a table that says which engine suits which
  kind of request (a diagnosis, a short question…). Google Gemini, ChatGPT and Claude
  can answer beside the local engines, when their key is set. Every call leaves one line
  in `ai-calls.jsonl`: who asked, which engine answered, how long, why that engine —
  never a word of the question or the answer. `ADR-0029`.
- **Moteurs IA.** A new screen shows the engines and their state, the policy, the counts
  by use, by kind and by engine, and the reason of the latest choices.
- **Poser une question.** A new screen for anyone signed in on the local network, without
  any knowledge of the machines. At the moment of sending, AIStack looks for personal
  data in the question (an e-mail address, a phone number, a postal address, bank or
  card details, a password, health, family, money, a date of birth). If it finds any,
  the question stays on your machines; otherwise the policy may let it go to an
  outside provider. The page says which engine answered and why. Nothing typed is
  kept after the session of the page: only the journal says that a question was asked.
- **Every card says whether its screen asks an AI.** A line under each card of the
  console, and a badge *IA* where an engine is asked, local or outside according to the policy.
- **Usage et empreinte.** A new screen counts the AI calls of the last 30 days (by
  use, by day, local or outside) and their energy and greenhouse gases (GWP at 100
  years) by level: the machine that answers, the network, the terminal of the person
  who waits, and the permanent load of AIStack. Every figure is a range, with its
  origin written beside it: measured, published by a source, or declared. The power of
  the GPU is read during a local call when `nvidia-smi` is visible. The method is
  inspired by the AFNOR SPEC 2314; AIStack does not claim conformity to it. `ADR-0030`.
- **Governed Heritage Engineering.** A page, and a block in the left column of the
  console, tell the method AIStack applies to itself and give the manifesto and its
  principles.

### Under the hood

- A copy of `ai_policy.yml` or `console_links.yml` made before a block or a screen
  existed is completed when it is read, so a new screen shows without editing the file.
  A copy of `ai_policy.yml` never receives a new *caller*, which only you can allow:
  see *To do when upgrading*.
- The shipped declarations grow by `ai_policy.yml`, `personal_data.yml` and
  `footprint.yml`, each read by a loader that refuses what it cannot read.
- Two findings of the heritage's own audit were closed: the integration tests of the
  official validation suite are back, re-measured, and each artifact of the Context
  Bundle now names its source relative to the repository (`GOV-0002/OS-095`, `OS-096`).

### To do when upgrading

- Set `AISTACK_VERSION=2.2.0` in `.env`, then `docker compose pull && docker compose up -d`.
  The new `docker-proxy` service is created.
- **A `config/ai_policy.yml` you edited keeps its callers**: to let the new question
  screen use an outside provider, add `portal.chat: external_allowed` under `callers:`.
  Without it, every question stays inside, which is the safe default.
- An engine you start on demand (the second local engine) must be declared as a service
  with `on_demand: true` in `service_categorization.yml`, or the health page reports it
  as running and undeclared each time it is up.
- The host service `aistack-engine-switch` is installed from the host, not by the image.

### Not changed

The installation script and assistant, the sign-in, the Dock, restore tests, the sync,
the restart watch, the new arrivals and the Time Machine work as in 2.1.0. Your
`./config` and your data are kept.

### Known limits

- The screen for personal data cannot recognise a bare first name, and only knows the
  words its definition lists (for instance «maladie», not yet «malade»). In doubt, a
  question stays inside; a question that holds none of the words can go outside.
- The footprint rests in part on declared figures (the permanent load of the containers,
  the making of the machine, the terminal) that are marked *to be confirmed*, and the
  permanent load dominates the total until it is measured. The GPU power is read in the
  web container; the vigil container cannot see it. Resource depletion and primary energy
  are not calculated.
- `ADR-0028`, `ADR-0029` and `ADR-0030` are Proposed; their open points are written in them.

`pytest -q` — 4013 passed; `mypy` — 650 files; 68 knowledge artifacts,
`blocking: 0   warnings: 0   clean: True`.

---

## 2.1.0 — 2026-11-18

**What 2.0.0 does, made accountable. AIStack 2.1 changes little of what you
click and a lot of what happens when you click: every chain leaves a trace, every
change made from a screen keeps its history, a declaration edited by hand is seen,
and the project can check its own documentation again. The principles the project
says it follows are back inside the product — and the code now answers to them,
measurably. `latest` names this version.**

*Why this release and how each part works, one concept at a time:*
`docs/04-handbook/GHE-IN-AISTACK.md`.

*One path change to know:* the `docs/` folders were numbered with two `03`; they are now
`00-foundation` to `03-governance`, then `04-handbook`, `05-development` and
`06-reference`. Links to the old `03-handbook`, `04-development` and `05-reference`
folders need the new number.

### What you may notice

- **A change made from a screen keeps its history.** The CPU priorities, a pair's
  selection, the SSH user names, a container declared from *Nouveautés* and the
  place chosen for the data are now written through one operation: the file is
  replaced whole or not at all; the previous one stays beside it as
  `<name>.avant-<date>-<time>`; nothing is written when the content is identical;
  and `declaration-change.json` records who, when, why and the fingerprints before
  and after — never the content. A new `*.avant-*` rule in `.gitignore` keeps these
  copies out of a git installation's tree.
- **A declaration edited by hand is seen.** Every pass of the vigil (every 15
  minutes) compares the 25 declarations with the copy it saw last. A hand edit is
  kept (`<name>.avant-observe-<date>`) and recorded as made *by hand on the host*. A
  file its loader no longer reads is reported **once** to Gotify, urgently, with
  the loader's own words and the last copy that read — nothing is refused and
  nothing is restored. Settings has a new section, *Déclarations modifiées à la
  main*: what cannot be read now, and the last twenty edits with their difference.
- **Every chain leaves a trace.** Health, architecture, console, the Time
  Machine's graph, the scan of the machines, the AI's reasoning, the observation
  of declarations and the integrity check run through one Runtime, and each run
  keeps a trace under `reports/generated/history/execution-trace/`: what asked,
  when, what came back — never a secret. Expect more files there than before: the
  vigil's passes now leave some. `python -m aistack.cli.ai_reason` prints the same
  report as before, and now leaves a trace too.
- **The selection screen says why.** Each item shows which rule decided it —
  ticked directly, ticked but already covered by a parent, inherited, or excluded —
  with a tooltip in French and in English. 2.0.0 had lost this explanation.
- **A fault of the sync is fixed.** A file whose name carries an accent (the
  library wrote it one way, the target folder rewrote it another: Unicode NFD
  against NFC) was linked and removed again at every pass — seven files in the
  reference library, each time. The target is now named in NFC and a second pass
  changes nothing.
- **An API keys file that is a list instead of a mapping now says so**, as every
  other declaration's loader already did.

### What came back from the heritage

2.0.0 removed from the product what governed the project's own documents. 2.1
brings back the part that has a use, and leaves the rest where it was.

- **The principles are in sight again.** The Constitution, the Glossary, the
  Manifesto, the principles registry and the protocols are in `docs/`, so that the
  code's own citations (`ARC-P-006`, `GOV-P-001`…) can be opened. What stays at
  the tag `archive/heritage-2.0.0-rc1` is declared in `FDN-0001`.
- **The Context Bundle and the integrity check are back**, run from a checkout of
  the repository: `python scripts/export_project_sources.py` writes the bundle,
  `python -m aistack.cli.knowledge_integrity <bundle>` runs eighteen checks on it
  and exits 1 when something blocks. They also run in the test suite. The Docker
  image carries the product, not its documentation, so the check there needs a
  bundle you bring to it.
- **A protocol for an AI agent** (`FDN-0013`, a Draft): how an agent acquires the
  project's knowledge from the bundle, and the Boot Report it produces — eight
  sections, ending READY or NOT READY. On 2026-11-18 an agent given only the bundle
  produced one, and named the commit it was taken from.
- **Still at the tag**: the package manager, the SSH transfer of the bundle, and
  seven of the eight integration test files of the official validation suite. They
  return when something uses them.

### Under the hood

- The Kernel names no technology and builds itself from `registrations.yml`; the
  providers come from it; eight Tasks run through its Runtime. The three copies of
  the health cockpit became one.
- Every departure from the principles that can be counted is counted
  (`scripts/ghe_audit.py`) and held by a test: on 2026-11-15 the Kernel named six
  technologies, 22 of 25 entry points never went through it and 35 files wrote on
  the disk outside a transaction; in 2.1.0 the first is zero, the second is 16
  declared exceptions (permanent monitors, status commands), and the third is zero,
  with 29 writes declared exempt and a reason each.
- The inventory of contracts could not see the Context Bundle's packages (seven
  directories lacked an `__init__.py`): fixed, found by the agent above.

### Not changed

The installation script and assistant, the sign-in, the Dock, restore tests, the
sync, the restart watch and the new arrivals work as in 2.0.0. The eight services
are the same. Your `./config` and your data are kept; there is nothing to set.

### Known limits

`FDN-0013` is a Draft, its qualification still to be decided; the verification of
the protocol with two models (`STD-0300`, 2.4) has not been done; and each artifact
of the Context Bundle names the directory it was generated in
(`GOV-0002/OS-096`). All three are decided for after this release.

`pytest -q` — 3314 passed; `mypy` — 593 files; 65 knowledge artifacts,
`blocking: 0   warnings: 0   clean: True`.

---

## 2.0.0 — 2026-11-15

**The first stable 2.0, validated by its owner on 2026-11-15: what
2.0.0-rc1 brought — an installation on a server that is not the
reference host, guided page by page, carrying nothing of that host's own
configuration — plus the three changes below, which came from running it
for a month on the reference host. `latest` now names this version.**

- **Restart after boot.** After a start of the machine, the new
  `restart-watch` service finds the containers that came up *running but
  stuck* — unhealthy, holding the network of a container restarted after
  them, or failing a probe you declare — and restarts them in the order
  their dependencies need. It acts for 30 minutes after it starts, only on
  a container seen stuck twice in a row, at most twice an hour each, and
  tells Gotify when one does not come back. The console has a card for it
  (the window, the stuck containers, the decision journal);
  `restart_watch.yml` holds the settings. `ADR-0025`.
- **New arrivals.** The vigil now says, once, a container that no service
  declares — after it was seen on two passes in a row, so a container that
  lives a few minutes is never announced — and the new console screen
  *Nouveautés* proposes it: its image, ports and GPU request, a prefilled
  name, category and description, and one click that declares it in
  `service_categorization.yml` (a dated copy is kept). A machine that
  answers SSH and runs Docker and that nothing declares is proposed too,
  with the lines to add to `hosts.yml`; `hosts.yml` takes an optional
  `address:`. The scan of the machines is off until `machine_scan_hours`
  in `arrivals.yml` says otherwise, and the image now installs `nmap` for
  it. `ADR-0026`.
- **The governance heritage left the product.** What 2.0.0-rc1 still
  carried to govern the project's own documents — the knowledge-integrity
  validator, the Context Bundle and the packages `item`, `policies`,
  `package_manager`, `knowledge` and `location`, which nothing in the
  product called — is removed, and `sync_context_bundle.sh` with it. It
  stays at the tag `archive/heritage-2.0.0-rc1`. A `2.0.0-rc2` was
  prepared for this and never published: its changes are in 2.0.0.
- **The maintenance page waits for nginx.** `maintenance_page.sh on`
  asked once whether the page answered, right after systemd said the
  service had started — before nginx was listening. It now asks again for
  up to 15 seconds (`AISTACK_MAINTENANCE_PAGE_WAIT`).

## 2.0.0-rc1 — 2026-10-10

**A release candidate: AIStack installs on a server that is not the
reference host, from nothing, guided page by page — and carries nothing
of the reference host's own configuration. Published to be tried on a
friend's server before 2.0.0; never tagged `latest`.**

- **`install.sh`** (`ADR-0023` § 4). On Debian, Ubuntu, Linux Mint or
  LMDE, as an ordinary account with `sudo`: it reads, then asks before
  each change — Docker Engine and the Compose plugin from Docker's own
  repository, `/srv/aistack` with `docker-compose.yml`, `.env`,
  `config/`, `data/`, `.env.web` (0600); on request Pocket ID, Gotify and
  Syncthing, each its own Compose project in `/srv/<name>`, and Ollama
  with `qwen2.5:3b`. It never prints a secret; run again, it redoes only
  what is missing; `--dry-run` says everything it would do.
- **The installation assistant** (`ADR-0023` § 5), `/setup/step/1…6`, on
  the local network only, opened by the token the script shows (`python
  -m aistack.cli.setup_token` shows it again): the host and its ports;
  the public address, with the proxy hosts to create in Nginx Proxy
  Manager and a check that both names answer; signing in — the Pocket ID
  procedure with the client's four addresses written out, the client's
  ID and secret, a fallback administrator's password hashed in the
  request, all kept in the data directory and never shown again; the
  host folders AIStack reads (`config/volumes.yml`, through
  `COMPOSE_FILE`); every API key with how to get it; a check of Pocket
  ID, Ollama, Gemini, Gotify and Syncthing; then the restart command.
- **A new installation carries nothing of the reference host**
  (`ADR-0023` § 7). The declarations AIStack ships were the reference
  host's own; they are now neutral, with an example in each comment, and
  the reference host's live with the tests. The local network to scan is
  discovered (`cidr: auto`); the thresholds that hold on any host apply
  to any host (`host: "*"`); without a declared publisher, the legal
  notice says the installation is private. **An existing installation
  keeps its own files**: at its first start, its copies become its
  owner's and never follow the neutral ones.
- **The troubleshooting assistant states the facts first.** For a
  finding: its evidence, what `backup_strategy.yml`, `pra_tests.yml` and
  `resource_priority.yml` say, then what to do — the how-to, the YAML to
  add and where, the command that verifies it, Apply for a CPU class, the
  result of a PRA test recorded from the page (`pra/scheduled.jsonl`,
  `pra_tests.yml` never rewritten). The AI's opinion is a click away:
  **Google Gemini first, given those facts, Ollama as the fallback**; the
  page says where the question goes before it is asked. A clickable
  notice on every page says when an answer is ready.
- **The vigil.** Every 15 minutes it renders the health cockpit and the
  console again and sends Gotify what changed — the score going down
  with its new findings, a silent host, a failed restore test, a Dock
  proposal waiting, applied, rolled back or failed — once, grouped.
- **Restore tests on a schedule**: every Sunday the sandbox restores
  every service with a recipe not tested in six days, and records it.
- **Two new health domains**: *Hôtes* (a host whose collector is silent)
  and *Données d'AIStack* — a 2 GB budget for AIStack's own data, old
  observations gzip-compressed in place after 90 days, never deleted.
- **Contents to devices** (`ADR-0022`): every content of the server to
  every Syncthing device, ticked directory by directory, with a quota per
  device, applied on the host with hard links; "Créer et partager le
  dossier", "Relancer le partage".
- **Settings → API keys**, for administrators on both addresses: every
  key `api_keys.yml` declares, entered, replaced, cleared or tested,
  write-only (the last four characters shown), each with how to get it.
- **The console**: the running version under the lockup; "Dock" in
  French; an "AI" mark on the screens that use it; pastilles on the
  cards with something waiting; "local network only" as each LAN card's
  last line.
- **The vigil renders, at its first pass, what a new installation does
  not have yet**: the Architecture page and the Time Machine's graph.
- **Not yet in a Docker-only installation** — what this candidate is
  meant to show: the Dock's executor, the scheduled restore tests, the
  sync executor and AIStack's nightly backup run on the host from a copy
  of the repository (`deploy/systemd/`), which `install.sh` does not set
  up; on such an installation those screens show and record, and nothing
  is applied on the host.
- **Fixes** found by the 2.0 acceptance tests on the reference host:
  the assistant read no network discovery in the image; a CPU finding
  shown could not be started once the next reading was calm; Gotify
  behind Cloudflare refused Python's user agent; an untouched copy made
  by hand never followed its shipped declaration; a Syncthing folder not
  yet created read "unreachable"; the installation token reached the
  access log.

`pytest -q` — 3502 passed; `mypy src` — 669 files; 90 knowledge
artifacts, `clean: True`.

---

## 1.11.0 — 2026-10-08

**The Time Machine now remembers what changes on the hosts themselves,
not only in their containers — packages, files, units — without ever
keeping a file's content.**

- **A collector on each host** (`ADR-0020`). One file,
  `aistack-host-collector`, written with the Python standard library
  only, so it runs on a host that has no copy of AIStack; started by
  systemd every 15 minutes, as root because part of what it watches
  only root can read, but read-only, with no network, writing only to
  its own directory. Installed on GIGABYTE and on the Raspberry, which
  writes to its backup disk that GIGABYTE already mounts.
- **What it records.** Every package installed, upgraded, removed or
  purged, dated by the host's own `dpkg.log` — the first run takes in
  every rotation still on disk, about eight months; every apt run, its
  command line and who asked; every file added, removed or modified
  under `/etc`, `/usr/local/bin`, `/usr/local/sbin`, in the crontabs and
  among the compose and `.env` files of the projects under `/srv` and
  `/opt` (more through `/etc/aistack-host-collector.conf`); every
  systemd service, timer, socket or path unit enabled or disabled.
- **Never the content.** A file is known by its size, mode, owner and a
  fingerprint keyed with a secret of the host's own, readable by root
  only: a short password in an `.env` cannot be found again from its
  fingerprint. The Time Machine says that a file changed and when,
  never what it says.
- **In the Time Machine.** After the graph is rebuilt, the ribbon has a
  third group, *Hosts*, one lane per host, one mark per event; an
  event's node says what changed. `python -m aistack.cli.hosts` gives
  each host's last run and events, and says a host whose collector has
  gone silent or whose records cannot be read.
- **Fixes.** The Quai's governed changes now reach the Time Machine's
  ribbon, as one `dock` stream, instead of each change appearing as a
  stream of its own.

## 1.10.0 — 2026-10-08

**AIStack makes its first change to a service — only the one an
administrator validated, after it was rehearsed on the latest backup,
with the way back ready and the reason kept.**

- **The Quai** (`ADR-0019`). Console → *Quai*, on the local network,
  signed in. For each service declared in `dock.yml` (WordPress to
  begin with), the page shows whether a newer image is published for
  the tag each container runs — the registry is asked, nothing is
  downloaded. An administrator proposes the update and writes why
  (required); an administrator validates it — in production, another
  than the author. A proposal can be rejected until it starts.
- **The dock's executor**, on the host (`aistack-dock.timer`, every two
  minutes, `python -m aistack.cli.dock list|show`). For a validated
  proposal, in order: the container still runs the image the proposal
  was written against and no longer carries Watchtower's label; a
  sandbox restore of the latest backup has succeeded within 24 hours,
  or one is run; the new image is fetched by its registry digest, never
  by a tag; the restore is rehearsed with it; the previous image is
  kept; the container is recreated with its own compose project; the
  live service is checked (the right image, running, healthy, no
  restart for 30 s, then WordPress's database, home and login pages).
  A failure before the change stops it with nothing touched; a failure
  after puts the previous image back and checks again. Every step is on
  the page with its duration and what it found.
- **Nothing changes without its why.** Once executed, the reason is
  recorded in the Time Machine as the explication of the container it
  changed, by its author; the change enters the provenance graph as an
  activity tied to the people who proposed and validated it, to the
  images before and after, to its outcome and to its explication.
- **One transaction.** A change runs as one transaction of operations
  through the kernel's transaction service — each operation's status
  kept, the first failure stopping the rest.
- **A healthcheck.** The web container answers `/healthz` on the
  local-network port; `docker ps` — and a dashboard reading Docker such
  as Homepage — shows it `healthy`.
- **Fixes.** The arrow in front of the console's two groups of screens
  showed as an unknown character.

On the reference host, WordPress's two containers no longer carry
Watchtower's label: they change only through the Quai.

## 1.9.0 — 2026-10-08

**A backup is proven by restoring it: AIStack now restores a service's
latest backup in a sandbox beside the running service, checks it, times
it and proposes the PRA-test entry — and it backs itself up.**

- **Restore tests in a sandbox** (`ADR-0018`). `python -m
  aistack.cli.sandbox restore <service>`, on the host: the latest backup
  restored with the image the service runs, on its own internal Docker
  network with no port and throwaway passwords, files on the local disk
  after a free-space check, everything removed at the end but the
  report. Each step is shown as it runs; the report gives every check,
  the measured time to recovery, and the `pra_tests.yml` entry it
  proposes — written only by you. Recipes: WordPress (database and
  `wp-content`, the site answering), Nextcloud (database), Immich
  (database, and photos of the external library taken back from Déjà Dup
  and compared with the database), AIStack itself (data, Time Machine
  graph rebuilt, the application started on it).
- **Compare with the running service** (`--compare`): rows per table and
  files per folder, backup next to live, biggest gaps first — numbers,
  no verdict. The live side is only read.
- **Rehearse going back before an upgrade** (`rollback <service>`): the
  image a container ran before its last upgrade, fetched again by its
  registry digest if it was removed, run with the latest backup in the
  sandbox; then the line to pin in the compose file. Going back for real
  stays yours. The digest collector now remembers each image's registry
  digests, so the next upgrade can be rehearsed.
- **AIStack in its own disaster-recovery plan.** A nightly backup
  (systemd timer, 03:00, 30 days kept, secrets included, mode 600) and a
  restore script into a new directory; the reference host's restore
  test recorded.
- **An action plan.** The Health Cockpit's two score badges lead to a
  page that ranks what to do by what it gains, for the health score and
  for technical debt, with a link into the assistant for each finding.
- **Shipped declarations follow the version.** A declaration you never
  changed is taken from the new version at start; one you changed is
  kept and shown in Settings → *Shipped declarations*, with the
  difference and the command to take the new one.
- **Code in quarantine.** Files believed unused wait six weeks behind a
  tripwire that records any use before they are deleted; they count as
  technical debt meanwhile (`OPS-0012`).
- **Fixes.** A backup disk mounted on demand, or a network share that
  does not answer, is a finding instead of a page that fails to render
  (the containers now see mounts made after they started); explications
  written in the same second are all kept; single-file mounts no longer
  show as disks; `/setup` shows the host's `./config` path; findings
  read in the page's language; no version number is shown on screen.
- **What the tests found on the reference host**, said rather than
  hidden: Nextcloud's files and Immich's uploads live on the backup disk
  itself with no other copy — declared as uncovered state until a copy
  exists.

`pytest -q` — 3249 passed; `mypy src` — 623 source files, no issues;
knowledge integrity — 85 artifacts, `clean: True`.

---

## 1.8.0 — 2026-10-04

**Pull the image, run AIStack: the Docker image is no longer only the
validator but the whole application, started by one compose file, and
a new installation says what it still needs before it is used. The
reference host itself now runs that way.**

- **One image, six services.** `bigbrother1969/aistack-core` runs the
  web application and the five collectors, each a service of
  `docker-compose.yml` on the host's network, with the Docker socket and
  the host's directories mounted at the same path, read-only. Set
  `AISTACK_VERSION` in `.env`, then `docker compose pull && docker
  compose up -d`. The knowledge-integrity validator is still in the
  image, as `docker compose run --rm validate` (`ADR-0017`, accepted).
- **The configuration outside the code.** Every declaration lives in
  `./config`, file by file: the first start copies those it lacks and
  never overwrites one, so an upgrade keeps yours and a screen's save
  (CPU priorities, SSH user names) is kept across restarts.
- **A guided first start.** Until the host, the identity provider and
  the OpenID Connect client are declared, every page shows **⚠ To
  configure**, leading to a public `/setup` page: what is left, in which
  file, the values in use today, and the manual's section — never a
  secret's value.
- **Choose where the data lives.** In Settings, under the new *Disks and
  mounts* section (every disk and mount the server sees, its free space,
  and what AIStack keeps on it), an administrator picks a disk from a
  list; AIStack records the choice and shows the commands that move the
  data to `<disk>/AIStack/data`, and the way back — it never moves
  anything itself.
- **A user manual**, from Help, French and English: every screen in
  detail, the initial setup, and troubleshooting. The README gains a
  *How to install* chapter: prerequisites (Pocket ID included),
  precautions, the steps, and Docker.
- **Development and production phases.** While an instance is set up
  (`phase: development`), what an administrator writes is validated as
  written, a session's test entries can be purged, and an ADR is
  accepted the day it is proposed; production brings back the second
  person and the day's wait (`ADR-0016`).
- **A fairer health picture.** The technical-debt score costs 15 points
  per domain carrying debt, once, instead of 15 per finding, so it
  moves when a domain is cleared (`OPS-0008`); a service started only
  when needed is declared `on_demand` and is no inventory gap when
  stopped; AIStack's own containers are declared services.
- **The reference host moved.** GIGABYTE runs the six compose services
  since 2026-10-04 — a preflight script, a host override file, and a
  documented way back; the git + systemd installation stays supported.

---

## 1.7.0 — 2026-10-03

**Users, profiles and the written "why": AIStack becomes one web
application people sign in to, where an administrator acts and a user
reads, and where the reasons behind things are written, confirmed or set
aside by people — not only imported.**

- **One web application.** The console and the five screens that each
  ran as their own process and virtual environment (Priority CPU, music
  selection, network discovery, the troubleshooting assistant, the Time
  Machine) are now one application, every route of it in the test suite
  (`ADR-0012`). It answers on two addresses: the public one, and the
  local network's (port 8186). The separate Selection UI image is
  retired. Every button, link and field now says what it does when
  hovered, and the licence page gives the Docker Hub image to pull.
- **Sign in with Pocket ID.** OpenID Connect against the owner's identity
  provider, its tokens verified by their signature; sessions kept on the
  server, ending after 8 hours idle or 7 days. A fallback administrator,
  protected by a password hash and locked after five failures, exists on
  the local network only — for when Pocket ID or Cloudflare is down
  (`ADR-0013`).
- **Profiles and rights.** Members of the Pocket ID group
  `aistack_admins` (and the fallback administrator) read and act; any
  other account reads only. Signed out, only the console, help and legal
  pages are public; Architecture and the Health Cockpit need a session.
  Every action requires the administrator profile and a token bound to
  the session. Pocket ID signs people in on the local network too.
  Settings show each person their profile; an administrator also sees
  every open session — and can close one — and a 30-day sign-in journal
  (`ADR-0014`).
- **Writing the why.** On a subject's *Pourquoi* page, an administrator
  writes an Explication (recorded as `Declared`, waiting for someone
  else's confirmation), validates one written by someone else or
  imported (becoming its second author), or discards one with a stated
  reason. Each act is one more version — nothing is ever deleted — and
  the graph links each version to the one it revises, and to its
  validator, at its next rebuild. A new *Explications* view lists the
  subjects that have one (81 on the reference host), filtered by status
  and by name (`ADR-0015`, proposed).
- **Fixed.** A subject named like an absolute path
  (`/media/BACKUP/nextcloud`) made its history file land outside the
  history directory; subject names are now always one file name.

**Upgrading.** `pyproject.toml` gains `PyJWT[crypto]`; install it in the
governed environment before restarting. Create the AIStack client in
Pocket ID with four addresses — the callback and after-logout URLs of
both the public address and `http://GIGABYTE:8186` (Pocket ID compares
them letter for letter) — and a group named `aistack_admins` allowed on
it; write its client ID and secret into `.env.web`
(`AISTACK_OIDC_CLIENT_ID`, `AISTACK_OIDC_CLIENT_SECRET`), and the
fallback administrator's hash from `python -m
aistack.cli.web_admin_password` (`AISTACK_WEB_ADMIN_SCRYPT`). The five
old screen services and their virtual environments can be removed.

3059 tests, 81 knowledge artifacts, `clean: True`.

## 1.6.1 — 2026-10-02

**The same evening as 1.6.0: what a real look at the reference host showed
the 1.5 collectors were doing to it, fixed — and a restart loop the Health
Cockpit had missed for three weeks, now caught.**

- **A Docker event stream that says what happened.** Four days of
  docker-events held 1.9 million events, 97 % of them `exec`: containers'
  own declared healthchecks, and AIStack's own package probes running in
  every container every 10 seconds. The collector now leaves out both —
  a `docker exec` a person runs is still recorded — and the history
  recorded before can be archived and refiltered in one command
  (`docker_events_refilter`, with `--healthcheck` to declare the probe of
  a container removed since). On the reference host: 1,942,964 events
  down to 14,379.
- **Collectors that leave the host alone.** Package inventories are taken
  once per image instead of every 10 seconds, and filesystem drift
  (`docker diff`) every 15 minutes; `dockerd` had sat above 100 % CPU
  permanently.
- **A graph that rebuilds in a minute.** Every projection re-scanned a
  stream's whole history directory once per instant; at tens of thousands
  of batches the rebuild ran for over an hour without writing anything.
  One scan per stream now (`latest_observations`).
- **Restart loops, caught.** A container dying at startup every 17 seconds
  (a SQLite database on NFS) read `running` at every instant the Services
  domain looked. It now also counts restarts over the last hour from the
  event history, threshold 5 (`OPS-0004`).
- **Nothing runs as root.** Every AIStack service unit now runs as the
  repository owner; none needed root. The publisher runs the governed
  chain once per pulled commit, not once per publishing step (`OPS-0002`).

2762 tests, 77 knowledge artifacts, `clean: True`.

## 1.6.0 — 2026-10-02

**The homelab's operational inventory declared and checked against what
really runs (roadmap R9/R10), the Health Cockpit's findings made actionable,
and three new read-only Time Machine views drawn from the validated
maquettes.**

- **Declared operational inventory.** AIStack's own LAN address and each
  of its services' ports are declared once, in a hand-written instance
  configuration, instead of typed into a dozen screens and links. Two new
  Health Cockpit domains, weighted 25 points each: *État persistant*,
  which checks that every service holding state has a declared backup
  strategy — SQL dump, stop-and-archive or live file backup, each grounded
  in a script or tool that really exists, a missing one declared as a gap
  rather than guessed — and *Écarts d'inventaire*, which reconciles, in
  both directions, the services declared for the homelab against the
  containers really discovered on the network. The *Tests PRA* domain now
  also flags a stateful service with no restore test on record, and never
  invents a result for one. Closed against the real homelab in the same
  release: 22 of the 29 inventory gaps found resolved, the last two
  unidentified containers identified and declared, three abandoned
  invoicing trials removed from the host rather than declared, the backup
  mechanisms of three services traced to their real timers and scripts,
  and eight services given a PRA-test entry — WordPress declared honestly
  as never restore-tested.
- **Findings you can act on.** The troubleshooting assistant now reads
  every finding the Health Cockpit raises, not only CPU and temperature;
  each red finding on the Cockpit links straight into it, and a console
  alert badge opens the matching Cockpit section. The one-click fix stays
  reserved to the CPU-priority action it was built for.
- **Time Machine: three new views.** A node's page now shows the network
  tree, that subject's own chronology and its facts side by side.
  *Reconstituer* shows a subject as it stood at a chosen instant, stream by
  stream — the latest observation at or before it, or an honest "nothing
  observed yet". *Pourquoi* lists a subject's recorded Explications,
  version by version. All three are read-only: the maquettes' writing
  actions (restore to a sandbox, correct or translate an Explication) are
  deliberately not built. On the ribbon, a cluster now unfolds into a list
  of its own members, the full list is grouped by stream as cards, and the
  tree and ribbon pages are cached and paginated so they stay usable on a
  production-sized graph.
- **Operations.** The four Docker collectors now run as the repository
  owner instead of root, so the observations they write stay rewritable by
  the rest of the stack. The Cockpit's weights register is brought back in
  line with its seven domains, and the console/Cockpit score drift seen
  while preparing this release is explained and given a procedure:
  regenerate both pages in the same sitting.

2726 tests, 77 knowledge artifacts, `clean: True`.

## 1.5.2 — 2026-09-30

**The Time Machine ribbon rebuilt around what a real production graph showed
it needed (`ADR-0011` § 26), and the graphic-debt catch-up the 26 September
charte graphique had left undone everywhere outside the three static
pages.**

- **Ruban du temps v2.** A real horizontal time axis per stream, not a bare
  chronological list — split into its own two real categories (the four
  Docker collectors, and everything else), each foldable with its own
  independent axis. Marks too close together to tell apart merge into a
  counted, still-navigable cluster; a second pass also accounts for a
  cluster's own label width, and a whole lane no individual marks can
  honestly represent any more (one production stream alone had accumulated
  49,125 instants) renders as a single summary badge instead. A navigation
  cursor opens the nearest instant on click, or on releasing a drag; on a
  touch screen, a tap does the same — deliberately short of drag-to-scrub,
  which would fight the same horizontal gesture the ribbon's own mobile
  scrolling needs. The ribbon and the network tree now cross-link by name
  (`aistack:stableSubject`) in both directions — a real but partial bridge,
  honestly labelled where it doesn't reach — and the ribbon's own stream
  filter now survives a language switch, like the tree and node screens
  already did.
- **Graphic-debt catch-up.** Two audits — `console.html`/`architecture.html`/
  `health.html`, then Time Machine's three older screens — closed every gap
  the 26 September charte graphique had left behind: a missing viewport
  meta tag and favicon, a residual pre-charte grey, a diagram collapsing
  unreadably on a narrow screen, five screens each hand-copying their own
  navigation bar instead of sharing one, and Time Machine's background,
  card borders and section titles never having received the charte at all.
  Every screen this project serves now shares the same background,
  borders, typography, and adapts to the real width of the window instead
  of a fixed column.
- **Console cards, rewritten.** The seven console cards' descriptions are
  now written for the person using them rather than the person building
  them — no internal host names or plan references, every description
  opens with what the card lets you do. Cards are now grouped by where
  they're reachable from ("Accessible depuis le réseau local" /
  "Accessible depuis internet"), each with its own colour band, rather
  than left to a paragraph of prose to explain.

2581 tests, 75 knowledge artifacts, `clean: True`.

## 1.5.1 — 2026-09-28

**1.5's fourth and last named collector, deferred past 1.5.0, plus the
first two GUI/interpretation pieces the roadmap's own maquettes
described (`ADR-0011` § 23-25): package inventory, a time ribbon, and
an upgrade correlation.**

- **Inventaire des paquets.** A running container's own installed
  packages, `docker exec` + `dpkg-query` first, falling back to
  Alpine's own `/lib/apk/db/installed` database, and `"none"` — never
  a silently empty list — when neither mechanism answers. Which
  mechanism actually responded is itself recorded as a graph fact.
  Runs as its own governed systemd poll, the same shape every other
  1.5 collector already holds.
- **Ruban du temps.** `timemachine_ui`'s third view (`/ribbon`): a
  single chronological list, one row per recorded instant, across
  every stream the graph currently holds — not only the four Docker
  streams. Each stream gets its own colour-and-shape badge (never
  colour alone), a collection gap is tagged rather than shown as an
  ordinary event, and every row links into the existing per-node
  provenance drill-down. A deliberately narrower v1 than the
  maquette's own full sketch — the stepping cursor, the paired network
  tree, and the event detail's "why" panel are named but not built
  here.
- **Corrélation upgrade.** The trigger the roadmap named ("Trace
  également les upgrades sur les containers docker") needed no new
  detection code: an image-digest change alone, already the local
  proof an upgrade happened per 1.5.0's own digest-drift collector.
  A new graph predicate links the package inventory nearest before
  that change to the nearest one after it, on the same subject, with
  no bounded time window — an unusually large real gap stays a
  visible, dated fact, never hidden behind an invented threshold.

2538 tests, 75 knowledge artifacts, `clean: True`.

## 1.5.0 — 2026-09-28

**The roadmap's third step for the Time Machine
(`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` § *1.5*, `ADR-0011` § 20-22):
passive traceability of what happens inside a container, upgrades
included — three of the section's four named collectors, each its own
governed polling loop feeding the same graph 1.3-1.4 already built.
The fourth, package inventory, is explicitly deferred past this
release — the owner's own decision, not yet cadred.**

- **Docker events.** Every container lifecycle action Docker itself
  reports — exec, pull, create, recreate, destroy — polled every ten
  seconds and recorded only when something actually happened, keyed by
  each container's own stable identity (a Compose `project/service`
  pair, never a Docker id recreation would break) so a subject's own
  thread survives being recreated.
- **`docker diff` périodique.** Every running container's own
  filesystem drift since creation, mount-path noise filtered out at
  the source against that container's own declared mounts (`docker
  diff`'s own volume exclusion is not reliable — verified against a
  real upstream defect before trusting it), written only when the
  value actually changed. A real production incident, found the same
  day it was enabled — `docker diff`'s own line order is not stable
  across repeated calls — is fixed at the source: this stream's own
  output is now sorted before comparison, so an unchanged container
  reads as unchanged.
- **Dérive du digest.** A running container's own current image
  digest, compared against the last one observed for the same stable
  subject — purely local, no registry call — the local proof an
  upgrade happened the moment `docker inspect` reports one.
- **Collection gaps recorded as their own fact** (R11), built once as
  a mechanism shared by every 1.5 monitor rather than three separate
  copies: a monitor that stops and restarts states the gap in its own
  coverage explicitly, rather than leaving a silent hole a later query
  could mistake for "nothing happened."

Every one of the three collectors runs as its own systemd service on
GIGABYTE, each verified against the real Docker daemon before being
left running, and each already rendering through `timemachine_ui`'s
existing generic per-node facts view with no new template code.

`bigbrother1969/aistack-core:1.5.0`, built from `1faad79`, digest
`sha256:7a81a42dbc0030fad27ead3a1d1d9f74f32096a5b3b85419e6f2392257ff1314`.
2473 tests, 75 knowledge artifacts, `clean: True`.

## 1.4.0 — 2026-09-28

**The roadmap's second step for the Time Machine
(`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` § *1.4*, `ADR-0011` § 18-19):
`timemachine_ui` gains two new views over the graph 1.3 built — a
foldable network tree read from the live catalogs, and a provenance
graph diagram centred on whatever node is being viewed. The roadmap's
third 1.4 item, the AI-drafts queue, stays explicitly open behind R8
(qualifying AI-explanation quality) — the owner's own decision was to
build the two ungated items now and revisit R8 at a later cadrage,
rather than assume `QUAL-0001`'s earlier closure already covers it.**

- **The network tree, `timemachine_ui`'s second view.** A foldable
  Réseau → Hôte → Stack → Conteneur hierarchy with search, built from
  the live Docker/Compose catalogs — never the graph, which carries no
  per-container business schema yet — with each node's real Historique
  looked up in the graph where one exists. Native `<details>`/
  `<summary>` gives the fold/unfold with no JavaScript at all. A remote
  host (reached only through an explicit, never-automatic SSH scan)
  attaches its containers directly, with no invented Stack level.
- **The provenance graph, `timemachine_ui`'s third view.** Every node
  page now also renders a Mermaid diagram of its own immediate
  neighbours — "centré sur l'étape," per the roadmap's own already
  validated maquette — reusing the same vendored Mermaid.js mechanism
  Architecture's own dependency view already draws real arrows with,
  rather than a second graph-rendering engine. Deliberately one hop
  only: a caller wanting to go further clicks through to a neighbour,
  one node at a time. A node with no real neighbour shows the same
  honest empty state every other section of the screen already uses.
- **Two of the roadmap's four already-validated Time Machine maquettes
  narrow their remaining gap.** A time ribbon and a full "why" panel
  still assume data (occurrence time, collection gaps, Explications
  woven through every stream) that 1.5 and 1.7 have yet to supply —
  `ADR-0011` states the gap explicitly rather than leaving it to be
  found later.

`bigbrother1969/aistack-core:1.4.0`, built from `c33f8dd`, digest
`sha256:afa0098bfcae644623e8555dbfd92d2ae58782a010dfe96a65a65b8e88160b68`.
2294 tests, 75 knowledge artifacts, `clean: True`.

## 1.3.0 — 2026-09-28

**The first step of the roadmap's Time Machine
(`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` § *1.3*, `ADR-0011`): AIStack's
own five histories, projected as a real PROV-O graph, browsable through a
new LAN-only screen, plus the "why" — Explications — read from four real
sources for the first time, commit history among them.**

- **The provenance graph is real, not only designed.** `aistack.timemachine`
  (Oxigraph, `pyoxigraph`) projects the four existing history streams plus
  the new Explications stream into a PROV-O graph — `prov:Entity`/
  `prov:Activity`/`prov:Agent`, `wasGeneratedBy`/`wasAttributedTo`/`used`,
  plus AIStack's own stable-subject, bitemporal and clock-source
  extensions. The files stay the source of truth; the graph is a
  projection, rebuilt in full on demand (`aistack.cli.timemachine_rebuild`),
  never incrementally, never scheduled. A filter runs before anything is
  indexed, excluding user-data volumes; secret-shape masking is
  deliberately not built yet — designed once a real secret shape actually
  turns up in the imported corpus, not guessed at in advance.
- **A fifth mini-app, `timemachine_ui`.** A new LAN-only screen (GIGABYTE,
  port 8186, same operational convention as Priorité CPU, Selection UI, the
  network-discovery screen and the troubleshooting assistant), read-only
  against the graph. Its v1 scope browses three levels — the streams, the
  instants each one recorded, and every fact known about one instant,
  including the reverse provenance edges back to an Agent or a causal
  request — deliberately narrower than the four richer maquettes the
  roadmap already validated (a time ribbon, a network tree, a "why"
  panel): those assume data (occurrence time, collection gaps,
  Explications woven through every stream) that 1.4 and 1.5 still have to
  supply, and building toward their visual richness ahead of that data
  would be exactly the invented infrastructure `ARC-P-006` forbids. Both
  languages, a responsive single-column layout on a phone, and an honest
  "not built yet" page when the rebuild has never run.
- **Explications, read for the first time, from four real sources.** A new
  `KnowledgeArtifact` kind (`STD-0100` gains a fourth confidence level,
  `Proposed`) answering "why" for a subject, always attributed, dated and
  versioned, never silently overwritten. Four sources now import into it
  for real: the AI Runtime's own `explain` answers, `pra_tests.yml`'s
  dated comments, this repository's five `claude/` session notes, and —
  last — its own commit history (240 of 695 commits carry a real
  conventional scope; the rest are skipped and counted, never guessed
  at). Each import is idempotent and a deliberate, owner-run act, never
  automatic.
- **`GOV-0002/OS-083` fixed at the source.** The two `claude/` notes whose
  own `status:` frontmatter broke `yaml.safe_load` since the day each was
  written (an unquoted colon-space sequence in their own prose) are
  corrected in place; a future re-import records a new Explication under
  each file's real `id`, alongside — never replacing — what was already
  recorded under the old, filename-derived one.

`bigbrother1969/aistack-core:1.3.0`, built from `a856006`, digest
`sha256:72a477a914d86bd3798fa9c5fa8e2f668afaa4dc5d7efb6608834e3c74f6dfd3`.
2270 tests, 75 knowledge artifacts, `clean: True`.

## 1.2.1 — 2026-09-27

**A same-day follow-up to `1.2.0`. A real defect the owner found using
the guided troubleshooting assistant in the browser: the AI Runtime's
answers came back in English regardless of the display language, and
regardless of the French-only instruction every prompt already ended
with — the opposite of what `1.2.0`'s own README bullet and
`ADR-0010`'s § *Consequences* claimed the day they were published.**

- **The AI Runtime's answers now follow the display language.**
  `reason`/`explain`/`recommend` (`aistack.ai_runtime.operations`) take
  a `target_language` — the CLI's own unchanged French default, or
  whatever language the guided troubleshooting UI's visitor is reading
  the page in — and, whenever that is not English, a second, fast
  model (`qwen2.5:0.5b`, declared as `translator_model:` in
  `ai_runtime.yml`, the same model already confirmed installed on this
  host, 2026-09-18) translates the answer into it. English needs no
  enforcement: the model's own unprompted behaviour already tends
  there, which is the very defect this release fixes for every other
  language. Left undeclared, `translator_model:` skips the pass
  entirely and every answer travels exactly as it did before this
  version — never blocked on a second model nobody confirmed is
  installed, the same guard `model` itself already gets.
- **`AIRuntimeAnswer` gains `language`** — the language `response` was
  asked to be in, carried alongside it into J7's own reasoning history
  (`aistack.ai_runtime.reasoning_history`) and into the guided UI's
  `step.html`, replacing the hardcoded `lang="fr"` and the note telling
  the English interface its answers were untranslated.
- **The now-inaccurate claims corrected**: README's own capability
  bullet, and `ADR-0010`'s § *Consequences*/§ *Open Points* (still
  `Proposed`, so revising it before its own acceptance changes nothing
  it already decided). What remains genuinely open is named in
  `ADR-0010` itself: the *quality* of a translated answer, in each
  language, is `R8`'s own prerequisite for `1.4`
  (`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md`) and still unmeasured —
  enforcing the right language is not the same claim as the answer
  being a good one in it.

`bigbrother1969/aistack-core:1.2.1`, built from `1843a62`, digest
`sha256:f3310341240def1190a7c55360d7308813bca138b53625ab63be399a845f76fe`.
2195 tests, 74 knowledge artifacts, `clean: True`.

## 1.2.0 — 2026-09-27

**The first version of the roadmap toward `2.0`
(`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md`, decided by the owner the same
day): from here on every step is numbered `1.2`, `1.3`… and `2.0` is the
end of that roadmap. `1.2` makes the console an application with its own
Settings page, and puts every screen of AIStack in French and in
English.**

- **The console is served by AIStack itself.** The standard library's
  static file server on port 8183 is replaced by a small server of
  AIStack's own (`aistack.console.server`, standard library only — no
  web framework added to the governed environment), same port, so the
  reverse proxy and every existing link are unchanged. It serves the
  console, Architecture and the Health cockpit, and a Settings page;
  anything else is a plain "not found", never a directory listing.
- **Settings, and a choice of language.** The Settings page lets the
  visitor pick the interface language. The choice is remembered by the
  browser (a cookie, one year) — users and profiles, and with them a
  per-user preference, come with a later version of the roadmap. A
  language switch, shown as flags, sits at the top of every page, next
  to the Settings link and — on every page but the console itself — a
  way back to the console.
- **Every screen in French and in English.** The console, Architecture,
  the Health cockpit and the four mini-apps (Selection UI, Priority CPU,
  network discovery, the troubleshooting assistant) all switch language.
  The console hands its language to each mini-app in the link, since a
  browser never shares a cookie between two addresses; each mini-app
  then remembers it for itself. French stays the reference language:
  anything a screen displays rather than says — container names,
  findings, notes, a service's declared description — is shown as it
  was written.
- **What stays in French.** The AI Runtime's answers in the
  troubleshooting assistant: their quality in English has not been
  measured, and the English interface says so on the page rather than
  presenting an unmeasured translation as equivalent.
- **Guarded by the test suite, not by care.** Every language must carry
  exactly the reference language's messages, with the same
  placeholders, none empty, and every message a screen — mini-apps
  included — asks for must exist; a missing translation fails the suite
  before it can reach a page.
- **Decision record.** `ADR-0010` (User Interface Localization) records
  these choices. It is published with this version as *Proposed* — the
  heritage's own rule since 2026-08-21 accepts a decision the day after
  it is proposed, and the owner chose not to hold the release for it;
  its acceptance, on 2026-09-28, changes no behaviour.

`bigbrother1969/aistack-core:1.2.0`, built from `eb4905c`, digest
`sha256:098f6dd0957e24a2a966e03b06ed0d2b5b793de3f6903d791682e4a7e224972c`.
2183 tests, 74 knowledge artifacts, `clean: True`.

## 1.1.1 — 2026-09-26

**A same-day follow-up to `1.1.0`. No new capability — `OPS-0009`'s own
PRA (restore-test) records catching up with real restore tests the owner
ran the same afternoon, and one real gap they found and closed. This
entry is about `src/aistack/pra/definitions/pra_tests.yml`'s own
hand-maintained history, not about code.**

- **Arrstack: a real backup gap found, then closed.** A real restore
  attempt against `/srv/arrstack/configs`, from the GIGABYTE Duplicity
  archive `OPS-0009` had assumed covered it, came back "not found in
  archive" — confirmed with a read-only listing: nothing under
  `arrstack` was ever in that archive. It turned out to be the owner's
  own Deja Dup backup of his personal document/media folders, never
  configured to reach `/srv`. Recorded `failed` first, not smoothed
  over. Closed the same day: a dedicated `backup-arrstack.sh` (stop the
  stack, `tar czf` its config tree to
  `/media/BACKUP/CONFIG_BACKUPS/arrstack/`, restart, keep the last 8,
  weekly cron), then a real restore test — extraction clean in 3m10.7s,
  every diff against the live tree explained by the stack having been
  stopped and restarted for the backup, nothing pointing at a bad
  extraction. Recorded `success`, `rto_minutes: 3`.
- **Raspberry: a real backup existed — this time actually proven, not
  assumed.** A pre-existing restic backup (16 real snapshots since
  2026-03-08) was found while investigating the Arrstack gap. A first
  restore attempt, targeted at `/tmp` — Raspberry's own 16 GB system
  disk, not the 9 TB drive the repository itself lives on — ran out of
  space and left several restored files genuinely corrupted: a real
  failure, recorded as one, and traced to the restore target rather
  than to the backup. Redone against `/media/BACKUP`: 1742 files, 1.164
  GiB, zero errors, every remaining diff explained by services that
  keep running while the snapshot was taken. Recorded `success`,
  `rto_minutes: 1`, covering six of Raspberry's seven stacks.
- **Vikunja: the seventh stack, closed the same day.** Vikunja's live
  MariaDB data directory is never safe to copy file-by-file while the
  database is running — the same reasoning this file already applies to
  Nextcloud and Immich. `backup_raspberry.sh` was extended to run
  `mariadb-dump --single-transaction` against `vikunja-db` before every
  restic backup. Verified, not assumed: a real run of the updated
  script produced a snapshot naming the new dump, its files restored
  and diffed empty against the live tree, and the restored dump loaded
  cleanly into a scratch, disposable MariaDB container — producing all
  34 real Vikunja tables. Recorded as a dated addendum to Raspberry's
  existing entry, since it changes what is covered, not the timed
  restore already recorded for the other six stacks.

`bigbrother1969/aistack-core:1.1.1`, built from `fa2b73d`, digest
`sha256:63a4727b8af21303a82d6217b45dd2769726288cb761f062344034ed0c1a3d8f`.
2081 tests, 73 knowledge artifacts, `clean: True`.

## 1.1.0 — 2026-09-26

**Everything below is what accumulated on top of `1.0.0` over eight days of
work that never bumped the version — this entry catches it up in one pass,
the same shape `0.6.0`'s own entry used for the same situation.**

- **AI Runtime: a slower but correct model.** `QUAL-0001`'s own governed
  experiment campaign found `qwen2.5:0.5b` — the fast default since
  `1.0.0` — answering a closed factual question incorrectly. The owner's
  own choice, 2026-09-25: switch the live AI Runtime to `deepseek-r1
  :1.5b`, which passed the same test, and raise the now-configurable
  timeout to 900 seconds to match it (deepseek-r1:1.5b averaged ~500s per
  call in that campaign, against qwen2.5:0.5b's ~15.7s) — comfortably
  above the slowest call observed, with real margin left rather than cut
  close. Reversible in one place, `ai_runtime.yml`, with the previous
  choice kept there as history, not erased.
- **Runtime diagnosis distinguishes idle from merely unclassified
  (STD-0300 § VS-4 criterion 4.1, advanced).** A container flagged for
  CPU nobody declared an expectation for now has its own logs, already
  read in the same sweep, checked for incoming HTTP traffic — the same
  evidence `OPS-0004`'s own reference incident used to call
  `aistack-selection-ui`'s consumption idle rather than legitimate. A
  quiet container reads as more likely at rest; one whose logs show real
  requests in the same window is told apart from it, in plain language,
  rather than flagged the same way either way. Not yet a closed
  criterion — this has run against fixture data and a first live sweep of
  the reference deployment, not yet the sustained evidence that would
  satisfy it outright, and an active session (the other half of the
  reference incident's own evidence) is still unchecked.
- **Runtime diagnosis reads a container's declared lifecycle for
  development-flag findings too (STD-0300 § VS-4 criterion 4.3,
  advanced).** A container `OPS-0003` declares — `frigate`, so far, the
  only one — now carries that context on a development-flag finding
  (`--reload` left enabled, the bug that started this whole capability)
  the same way it already does on every other finding this run produces.
  Stays `not verified`: `OPS-0003` still names one container, and no
  development flag has ever actually been observed on it.
- **A stale governance claim corrected.** `OPS-0001` had stated, since
  2026-09-04, that STD-0300 § VS-4 criterion 4.5 remained unverified —
  true when written, false since `evaluate` satisfied it on 2026-09-11.
  Corrected; nothing about what the register actually declares changed.
- **CMDB HTTP probe.** `architecture.html` gained a real-time section:
  every declared HTTP endpoint on the homelab (~46 of them) is asked for
  its status right now, and shown reachable-with-a-code or unreachable —
  a fact refreshed on every regeneration, not remembered from the last
  time someone checked.
- **Health Cockpit: a fifth scored domain, "Dette technique."** Alongside
  Storage, Services, Backup/DR and GPU, findings `OPS-0004` qualifies
  `technical-debt` are now scored into their own card, weighted the same
  as the existing Services domain — the owner's own choice, since the
  reference incident this card was seeded on (containers stuck after a
  power outage) is the same one Services already scores.
- **Foundation work toward a verified iPhone photo offload, not yet a
  finished pipeline.** Two pieces of a larger plan
  (`claude/PLAN-PHOTOS-IPHONE-NEXTCLOUD-IMMICH-2026-09-18.md`) landed:
  `NextcloudProvider` observes what one Nextcloud folder actually holds,
  and `verify_uploads` confirms a file it reported is really, fully
  present — checking the size Nextcloud's own WebDAV answer claims
  against a second, independent download's real byte count — before
  anything later in the plan would treat a photo as safe to erase from
  the phone. Nothing yet triggers that later step; this is the checking
  machinery it will need, built and tested on its own first.
- **Fixed:** a callable, one-argument `Protocol` was reported satisfied
  by 192 classes across the package — nearly every concrete class the
  inventory can import — instead of the one real function it was written
  around, because conformance was checked only on the contract side.
  Reading `__mro__` on the implementation side too closed it
  (`GOV-0002/OS-059`).
- **Fixed:** a second, independent `KnowledgeArtifact`/`KnowledgeProvenance`
  definition had existed since 2026-07-22, unwired, alongside the one
  every real provider, the Context Bundle and `transport` actually fill —
  merged into the one production model and removed
  (`GOV-0002/OS-058`).
- **Fixed:** the AI Runtime's own test suite printed a `BrokenPipeError`
  traceback on every run, from its mock Ollama server writing a response
  after the one test using a slow answer had already let its client time
  out. Cosmetic and test-only — `OllamaEngine` was never the thing at
  fault, the test proving the timeout is reported rather than raised
  passed before and after — but noisy enough on a frozen release to fix
  rather than carry forward.
- **Quiet foundation work, no visible capability yet:** contracts and
  interfaces for a `PackageManager` (`ValidationEngine`,
  `IntegrationEngine`) — a receiving dock for a future knowledge-package
  mechanism `ARCH-0009`/`ARCH-0013` already describe, not yet wired to
  anything a user reaches.

`bigbrother1969/aistack-core:1.1.0`, built from `3ef455b`, digest
`sha256:1e1433da6056d940ab2ddf02537f8df264e80eada524d5868b125cde19185e10`.
2078 tests, 73 knowledge artifacts, `clean: True`.

## 1.0.0 — 2026-09-18

**The first version this project calls 1.0.** Not because one feature
crosses a line, but because the two halves the whole `PLAN-TRAJECTOIRE`
arc (J1 through J8) was building toward are now both real and connected:
a governed, explainable knowledge base of the infrastructure (Foundation
through the Health Cockpit and Architecture views, 0.1.0 through 0.7.0),
and — new since 0.7.0 — a reasoning layer that can look at a real
qualified finding, explain it in plain language, suggest what to do about
it, and now, for the one case safe enough to automate without guessing at
a judgement call, actually apply the fix and verify it worked. Everything
below is what was added on top of `0.7.0`; the section further down,
*Everything AIStack does, as of this release*, is the complete picture,
not just this version's delta.

- **AI Runtime (J6).** Three governed operations —
  `reason`/`explain`/`recommend` — run a real `RuntimeFinding` through a
  local Ollama model (`qwen2.5:0.5b`, declared in `ai_runtime.yml`) and
  return grounded, explainable text. `recommend` never executes anything
  by itself: every prompt states this explicitly, not only the
  documentation around it. Wired end to end into
  `aistack.cli.ai_reason`.
- **AI Reasoning History (J7).** Every `reason`/`explain`/`recommend` run
  is persisted per subject (`reports/generated/ai-reasoning/<subject>
  .json`), version-stacked so a second run over the same finding adds to
  the record rather than replacing it — full prompt and response kept,
  never only a summary.
- **J8 — the chain proven live, and closed.** A real sweep of the
  reference deployment produced three genuine qualified findings, each
  carried all the way through `evaluate → reason/explain/recommend` with
  `reachable: true` answers and a full, traceable history entry. Closed
  without new code beyond a configuration fix (`ai_runtime.yml`'s host
  corrected from an unreachable hostname to the real bound address,
  `127.0.0.1`) — J6 and J7 already did everything J8 asked for.
- **Assistant de pannes — a guided, step-by-step interface over that
  chain.** A new LAN-only mini-app (`troubleshooting_assistant_ui`,
  GIGABYTE:8185, a sixth console card) walks the owner through a real,
  currently-qualified finding one step at a time: the finding itself,
  then `reason`, `explain`, `recommend` — modeled on how the owner and
  this project's own AI assistant already work together. Traceability is
  recorded the moment the walkthrough starts, never conditional on
  finishing it.
  - AI-generated answers now respond in French, everywhere this runtime
    is called from (the CLI included, since both share
    `aistack.ai_runtime.operations`) — the finding's own governed
    `interpretation`/`remediation` text stays in English, since that
    text is declared by `OPS-0004`, not generated.
  - A loading indicator during the guided flow's ~45s AI round-trip, and
    a hand-written (never AI-generated per finding) `/aide` page
    explaining how to open a terminal, find the host on the LAN, and
    connect over SSH — for a possibly non-technical reader following a
    remediation step.
  - **Propose → apply → verify.** The `recommend` step now carries an
    "Appliquer" button alongside its suggestion, scoped to exactly one
    safe, single-click action: classifying the finding's subject as a
    `background` container in the governed resource-priority definition
    — the same write `priority_ui` already makes in production, never
    anything derived from the AI's own free-text suggestion, and never
    the broader "priority" classification, which needs a real judgement
    call (a detector, CPU thresholds) no click can safely default.
    After applying, the diagnostic is re-run immediately and the result
    — corrected, or not — is shown plainly, never assumed. Verified
    end to end against a freshly provoked test case: proposed, applied,
    and confirmed gone from the next diagnostic sweep.
- **Selection UI and Priorité CPU closed to LAN-only.** Until this
  version these were the only two console cards reachable from the
  public internet (`https://selection.persiaut-family.fr`,
  `https://priority.persiaut-family.fr`, behind Nginx Proxy Manager).
  Closed at the owner's request — `console_links.yml` now points both
  at their direct LAN address, the same shape Découverte réseau and
  Assistant de pannes already used. The console itself, Architecture and
  Cockpit Santé stay reachable from outside the LAN, unchanged.

`bigbrother1969/aistack-core:1.0.0`, built from `2d1bf58`, digest
`sha256:d65c768584def01e8905630dd25da75bc45f8b2948b7eefb4ee7af89872c1776`.
1815 tests, 73 knowledge artifacts, `clean: True`.

## 0.7.0 — 2026-09-12

**Everything below is what `PLAN-J11-CONSOLE-2026-09-11.md` §10 and §11
added on top of `0.6.0`, the same day: `architecture.html` grows three new
sections, and AIStack can now see Docker containers on machines other than
the one it runs on.**

- **Docker dependency graph.** `architecture.html` gained a new view: the
  real `depends_on:` relationships between containers, read straight from
  each Compose project's own `docker-compose.yml` files — a project's
  containers shown as a connected graph, not a flat list, an arrow drawn
  only where a real dependency was actually read, never guessed.
- **External network topology and hardware inventory.** A new section
  names what sits outside the Docker layer entirely: the external services
  the homelab depends on (registrar, DNS/CDN, router, mail) and the two
  physical machines that run everything — model, CPU, RAM, disks, GPU —
  as a declared fact sheet instead of something to remember.
- **Live health metrics from Beszel.** Another new section reads real-time
  status, CPU, memory, disk, temperature, load and uptime for every system
  Beszel already monitors, shown alongside the rest of the architecture
  page instead of in a separate tool.
- **Network-wide Docker discovery.** A new, explicitly-triggered command
  (`aistack.cli.network_docker_discover`) scans the declared LAN, tries
  each declared SSH username against every host it finds alive, and
  reports back every Docker container running anywhere on the network —
  not only on the one machine AIStack itself runs on. Its first real run
  found containers on two machines this project had never observed
  before.
- **A LAN-only screen to manage that scan's candidate SSH usernames**, a
  new fifth card on the console, so adding a machine to the scan no longer
  means hand-editing a YAML file over SSH.

Before this build, `0.6.0` was re-verified against its recorded digest
(`GOV-0002/OS-047`) — pull matched.

`bigbrother1969/aistack-core:0.7.0`, built from `0f511b6`, digest
`sha256:61a18a664a2e41d22c2e682b1cc0d1e0d09e57806c2b92f3cde44f091013c5ba`.
1751 tests, 73 knowledge artifacts, `clean: True`.

## 0.6.0 — 2026-09-12

**Everything below shipped in the eight days since 0.5.0 — the version number
just never moved while it did. This entry catches it up in one go, and also
carries `evaluate` (below), which had briefly used this same number and lost
it to an undocumented revert — explained where that entry now stands,
retracted.**

- **`architecture.html`, rendered for real.** AIStack's own topology graph —
  built from the same Docker infrastructure discovery `0.5.0` already had —
  is now a self-contained page instead of only raw catalog JSON.
- **Health Cockpit.** One scored dashboard across four domains: Storage,
  Services, Backup/DR, and GPU. Each domain is instrumented against a real
  incident or a real declared threshold on the reference host, not a
  generic rule guessed in the abstract.
- **Console — one entry point for everything above.** A single page linking
  Selection UI, Priority CPU, Architecture, and Health Cockpit. All four are
  now reachable over HTTPS from outside the LAN, not just on the local
  network.
- **Quiet foundation work, no visible capability yet:** a shared event/
  version/provenance model that the project's four separate history
  mechanisms now all speak, and governed contracts for evidence,
  observation, collection and correlation. This is what the next phase (a
  full historical "time machine" — replaying what the system knew at any
  past moment) is built on, not a feature in itself yet.
- `ruff` and `mypy` adopted project-wide, gated in the same publishing
  chain as everything else.

`bigbrother1969/aistack-core:0.6.0`, built from `4d68ffc`, digest
`sha256:28a3e4e621d83c563725e08fd6e774158f2752b0d4e3a2008f60c1496a986a47`.
1549 tests, 73 knowledge artifacts, `clean: True`.

## 0.6.0 — 2026-09-11, retracted 2026-09-12

**The finding described below is not retracted — it ships in `0.6.0` above,
same as everything since `0.5.0`. What's retracted is only this entry's
claim to the tag: `pyproject.toml` reverted to `0.5.0` the same day this
entry was built (one unlabeled commit, folding in the Storage domain
alongside the version line, with no doc update to match), so by the time
the entry above needed a number, `0.6.0` was free again rather than taken.
Kept here rather than erased — the same reasoning `1.0.0`, right below,
already gives for the same kind of correction. The image itself is
preserved, retagged `bigbrother1969/aistack-core:0.6.0-retracted` now that
the live `0.6.0` tag points elsewhere.**

**The first qualified finding, derived end to end: two separately-collected
pieces of evidence correlated into one governed conclusion for the first
time. VS-4 closes three more criteria (4.2, 4.4, 4.5).**

- **New: `evaluate`.** Unexplained CPU consumption — a container using
  resources nobody declared an expectation for — is now correlated against
  the host's own temperature, at or above each sensor's own declared
  threshold, into one `RuntimeFinding`: `energy inefficiency` alone, or
  `energy inefficiency` and `sustainability anomaly` together when the host
  also reads hot. Wired end to end into `runtime_diagnose`: a live sweep of
  the reference deployment reports these the same way it already reports a
  log-signature finding.
- **New: a finding can cite a reading, not only a log line.** A
  `CitedReading` attaches the raw CPU or temperature reading a provider
  collected to a finding, named by the provider that collected it (`docker
  stats`, `sensors`) — alongside the existing log-line evidence, unchanged.
- Host temperature is read in a live sweep for the first time —
  `HostProvider.collect_temperatures` existed since `0.5.0` but nothing
  called it.

`bigbrother1969/aistack-core:0.6.0-retracted` (built as `:0.6.0`), built
from `a823190`, digest
`sha256:203bec639e4bae1240bc1d19bd9485e7eb2c24f185565aa23f7f2925c07e3109`.
1191 tests, 69 knowledge artifacts, `clean: True`.

## 1.0.0 — declared 2026-09-11, retracted 2026-09-11

Declared prematurely, on the mistaken assumption that the first qualified
finding (`evaluate`, below) was the 1.0 boundary. It is not: the same day
this version was declared, a separate, richer predecessor project was
recovered — a homelab health dashboard, a technical-debt score, and an
interactive architecture cartography, none of it living in AIStack yet —
and the project's own trajectory reserves 1.0 for the point where that
integration is complete
(`claude/PLAN-J6-HOMELAB-DASHBOARD-INTEGRATION-2026-09-11.md`), not for
`evaluate` alone. Corrected to **0.6.0**, below — same work, same day.
Kept here rather than erased, so the record shows what was renumbered and
why — the same reasoning `0.1.0`'s entry gives for the same kind of
correction.

`bigbrother1969/aistack-core:1.0.0`'s digest was pulled and re-verified
against its record before the corrected build (`GOV-0002/OS-047`) — it
matched: `sha256:efcb70b1a3be5d71f444d91a0483b5a632def704815079e80f1434976d5823c3`.
No divergence; the tag simply named the wrong version.

## 0.6.0 — 2026-09-11

**The first qualified finding, derived end to end: two separately-collected
pieces of evidence correlated into one governed conclusion for the first
time. VS-4 closes three more criteria (4.2, 4.4, 4.5).**

- **New: `evaluate`.** Unexplained CPU consumption — a container using
  resources nobody declared an expectation for — is now correlated against
  the host's own temperature, at or above each sensor's own declared
  threshold, into one `RuntimeFinding`: `energy inefficiency` alone, or
  `energy inefficiency` and `sustainability anomaly` together when the host
  also reads hot. Wired end to end into `runtime_diagnose`: a live sweep of
  the reference deployment reports these the same way it already reports a
  log-signature finding.
- **New: a finding can cite a reading, not only a log line.** A
  `CitedReading` attaches the raw CPU or temperature reading a provider
  collected to a finding, named by the provider that collected it (`docker
  stats`, `sensors`) — alongside the existing log-line evidence, unchanged.
- Host temperature is read in a live sweep for the first time —
  `HostProvider.collect_temperatures` existed since `0.5.0` but nothing
  called it.

`bigbrother1969/aistack-core:0.6.0`, built from `a823190`, digest
`sha256:203bec639e4bae1240bc1d19bd9485e7eb2c24f185565aa23f7f2925c07e3109`.
1191 tests, 69 knowledge artifacts, `clean: True`.

## 0.5.0 — 2026-09-04

**A stabilization release: no new capability, eight pieces of tracked debt
closed, two real defects fixed.**

- The open-item register (`GOV-0002`) went from eight open entries to
  zero. Among them: three foundational documents (the principles
  registry and the two testing-environment standards) moved from `Draft`
  to `Published`; the deployment host now has a named, verified way to
  run AIStack without hand-setting `PYTHONPATH` on every command
  (`ADR-0001` § *Deployment host*).
- **Fixed:** the Context Bundle always reported its own repository
  location as `"unknown"`, even when the information was sitting right
  there in the bundle's own manifest. It now reads it.
- **Fixed:** files moved to the archive folder (`docs/99-archive`) were
  still being treated as part of the governed knowledge base instead of
  being set aside — the exclusion existed for `docs/99-meta`, one
  directory over, and missed this one by a name.
- **First real exercise of the "an image stays verified" rule**
  (`GOV-0002/OS-047`): before this version was built, `0.4.0` was pulled
  back from Docker Hub and its digest checked against the one on record —
  it matched.

`bigbrother1969/aistack-core:0.5.0`, built from `57290fa`, digest
`sha256:3def537335f5f9f36d2824f2c6d56e0c4f5c7232017be36b93bf78a307816896`.
940 tests, 66 knowledge artifacts, `clean: True`.

## 0.4.0 — 2026-09-03

**The CPU priority feature generalizes from one hardcoded app to any
number of declared ones.**

- What used to be "watch Jellyfin, throttle these fourteen named
  containers" became a declared list: any container can be named a
  priority app, each with its own CPU ceilings and its own way of
  detecting activity — asking an app's own API (as Jellyfin already did)
  or reading its live CPU usage for a container with no API of its own.
- A container Docker reports that nobody has classified is now left
  alone entirely, rather than assumed to belong to the fourteen-name
  list.
- New screen: `priority_ui`, to add, edit or remove a priority app or a
  background container without hand-editing YAML.
- CPU boost/throttle decisions are now written to a queryable history —
  when a container was boosted, why, and for how long.

`bigbrother1969/aistack-core:0.4.0`, built from `8757605`, digest
`sha256:daf46c76b309e047c8801a25857b1328c01fc69c84c25d1ac333e05c8bb2f9fb`.
853 tests, 66 knowledge artifacts, `clean: True`.

## 0.3.0 — 2026-09-03

**Two new capabilities, running live on the reference host.**

- **Resource priority monitor**: while Jellyfin is playing something,
  AIStack gives it more CPU and turns the rest of the background
  containers (the `*arr` stack, torrent client, etc.) down — then puts
  everything back once playback stops. Runs as its own service on the
  host.
- **Selection UI redeployed as a systemd service**, off the ad hoc
  terminal session it used to need.

`bigbrother1969/aistack-core:0.3.0`, built from `7fab030`, digest
`sha256:55f9cd02711462306eb434a6c4184936b7a7fa1a28ddc7f374bea2248fde0376`.
823 tests, 66 knowledge artifacts, `clean: True`.

## 0.2.0 — 2026-08-29

**The first image published under a governed procedure.**

`0.1.0` (below) had shown what publishing without one costs. `OPS-0002` §
*Publishing an image* exists because of that, and this is the first build
to go through it: a clean tree, `main`, `HEAD` equal to the published
commit, and a passing suite, checked in that order before the image is
built at all.

`bigbrother1969/aistack-core:0.2.0`, built from `0a7ec1a`, digest
`sha256:3ee7cf1fae80cce7c84f404f5354f5edeeeddbf950e299c4a2a8dcb1f4aa194f`.
668 tests, 66 knowledge artifacts, `clean: True`.

## 0.1.0 — 2026-08-19, deleted 2026-08-23

The first published image, built without the procedure `0.2.0` introduced.
It carried compiled bytecode the project's own knowledge base had no
record of. Rather than rebuild it retroactively, the owner deleted it —
`GOV-0002/OS-011` records the reasoning: *"a rebuilt image would have to be
verified before publication and then stay verified; an image nobody pulls
cannot diverge from the heritage that describes it."* Kept here rather than
erased, so the record shows what was unpublished and why, not just what
survived.

---

## Everything AIStack does, as of this release

Not what changed — what runs, as of 1.4.0 (2026-09-28), taken together.

- **Docker infrastructure discovery.** Point AIStack at a Docker host and
  it produces a governed catalog of what is running: identity, image,
  state, published ports, mounts, and the real `depends_on:` relationships
  between containers, read from each Compose project's own files —
  regenerated the same way every time, from the host, not from what
  someone remembers about it.
- **Architecture, visualized.** `architecture.html` renders that same
  discovery as a self-contained topology graph, plus a Docker dependency
  view, a section naming the external network topology and the hardware
  each machine runs, a live Beszel health-metrics section, and — as of
  1.1.0 — a real-time CMDB section asking every declared HTTP endpoint on
  the homelab for its status right now — a real page, not raw catalog
  JSON, kept current every time it's regenerated.
- **Network-wide Docker discovery.** A separately-triggered scan of the
  declared LAN, over SSH, reports Docker containers running on machines
  other than the one AIStack itself runs on.
- **Health Cockpit.** One scored dashboard across five domains — Storage,
  Services, Backup/DR, GPU, and — as of 1.1.0 — Dette technique — each
  instrumented against a real incident or a real declared threshold on
  the reference host.
- **AI Runtime and Assistant de pannes — new as of 1.0.0.** A real
  qualified finding can be reasoned about, explained in plain language,
  and given a suggested next step by a local Ollama model
  (`deepseek-r1:1.5b` as of 1.1.0, chosen over the faster `qwen2.5:0.5b`
  after a governed test found the faster model wrong on a factual
  question), in French — never a source of truth, never an executor,
  every prompt says so itself. A guided, step-by-step interface
  (`Assistant de pannes`)
  walks a real finding through this chain one step at a time, and can
  apply the one safe, single-click fix this project trusts a button to
  make on its own (declaring a container `background` in the resource
  priority definition) — always re-verified against a fresh diagnostic
  afterward, never assumed to have worked. Every reasoning call is kept
  in a durable, per-subject, version-stacked history.
- **Console.** One entry point linking Selection UI, Priority CPU,
  Architecture, Health Cockpit, the network discovery screen and the
  troubleshooting assistant, all reachable from the same page. Only the
  console itself, Architecture and Cockpit Santé are reachable from
  outside the LAN — Selection UI and Priorité CPU joined the rest
  (network discovery, the troubleshooting assistant) as LAN-only as of
  1.0.0. As of 1.2.0 the console is served by AIStack itself, has a
  Settings page, and every screen — console, Architecture, Health
  Cockpit and the four mini-apps — is available in French and in
  English, the choice following the visitor from one screen to the next.
- **Context Bundle — self-onboarding for an AI assistant.** A single
  portable archive carries the project's whole governed knowledge base,
  with a manifest that proves what commit it was taken from and lets a
  recipient verify two bundles carry the same content without trusting
  whoever sent it. This is how a new AI session, or a new contributor,
  gets up to speed without reading the repository's entire history.
- **Time Machine and Explications — new as of 1.3.0, two more views as of
  1.4.0.** AIStack's own five histories, projected as a real PROV-O graph
  (Oxigraph), rebuilt in full on demand, browsable through a new LAN-only
  screen — streams, the instants each one recorded, and every fact known
  about one instant, including the provenance edges back to whoever or
  whatever caused it. The "why" itself, Explications, is read for the
  first time from four real sources: the AI Runtime's own answers,
  `pra_tests.yml`'s dated comments, this project's `claude/` session
  notes, and its own commit history — each import deliberate, attributed,
  and never silently overwritten. As of 1.4.0, two more views: a foldable
  Réseau → Hôte → Stack → Conteneur tree read from the live catalogs, with
  search, and a Mermaid provenance-graph diagram on every node page,
  centred on the node being viewed and its immediate neighbours.
- **Knowledge integrity validation.** Eighteen checks run against the
  governed documentation on every test suite and before every
  publication — missing metadata, broken cross-references, undated
  claims about a moving system, decisions nobody recorded as implemented
  or abandoned, and more. `clean: True` is what gates a release.
- **Runtime diagnosis.** A sweep of the Docker host, no container named,
  qualifies log lines against declared signatures, flags CPU consumption
  and development options (like `--reload`, the bug that started this
  capability) left enabled in a permanent service — and, as of 0.6.0,
  correlates unexplained consumption against the host's own temperature
  into one finding citing `OPS-0004`'s vocabulary: energy inefficiency
  alone, or energy inefficiency and sustainability anomaly together when
  the host also reads hot. As of 1.1.0, a consumption finding also states
  whether the same container's own logs, read in the same sweep, show
  incoming HTTP traffic — telling apart a container plausibly at rest
  from one that is merely unclassified but busy — and a development-flag
  finding is grounded against the same declared lifecycle context
  (`OPS-0003`) every other finding already is. Every finding cites the
  evidence it was built from — a log line, or a raw reading.
- **CPU resource priority scheduling.** Declared priority applications
  (Jellyfin, as of 0.5.0) get more CPU while active and give it back once idle;
  everything else is throttled down for the duration. Detection is
  pluggable — an app's own API, or its live CPU usage — and every
  boost/restore decision is recorded, queryable later.
- **Music sync selection.** Choose, under a real capacity limit, what
  part of a media library syncs to a device — a checkbox screen backed by
  a tested selection engine, materializing the result by hard link rather
  than by copy, and telling the truth about what's selected, what's
  built, and what's actually landed on the device.
- **A governed documentation heritage, self-applied.** Every architectural
  decision, standard, and open question this project has is itself a
  checked, cross-referenced, versioned knowledge artifact — including the
  register that tracks what is still open (`GOV-0002`) and the procedure
  that governs how a change reaches the world (`OPS-0002`). AIStack's
  claim that infrastructure knowledge can be governed is tested against
  itself first.

---

## Related Artifacts

- `OPS-0002` — Heritage Publication, § *Publishing an image*, § *Recording
  what's new*
- `GOV-0002` — Open State Register
- `docker-compose.yml` — the digest that proves each build, alongside the
  summary this document gives it
