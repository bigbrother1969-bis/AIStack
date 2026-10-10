---
artifact:
  id: ADR-0023
  title: Installation Assistant
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.4
  status: Accepted
  owner: Architecture
  created: 2026-10-10
  updated: 2026-10-10

relations:
  references:
    - ADR-0014
    - ADR-0016
    - ADR-0017
    - ADR-0022
---

# ADR-0023 — Installation Assistant

## Status

Accepted, 2026-10-10: the owner's answers of the same day decide § 1–3;
§ 4–6 is the architecture that follows from them, written here so it
can be contested before the code exists. `ADR-0016` § 3 allows
acceptance the day of the proposal in the development phase.

## Context

The 2.0 plan ends with an installation from scratch on a friend's
server (ServerLinuX, LMDE 7), by the owner, following the manual — the
manual is what that test checks. Today a new installation is the
manual's ten steps (§ *Mise en route d'une nouvelle installation*)
and, with Docker, the `/setup` page (`ADR-0017` § 4), which lists what
is still to declare but changes nothing: every declaration, secret and
path is written by hand in `./config`, `.env.web` and
`docker-compose.yml`.

Three things are left to the person installing, with no help from
AIStack:

- the prerequisites — Docker, the identity provider (Pocket ID), the
  local AI (Ollama), the notifications (Gotify), the device sync
  (Syncthing);
- the API keys, and how to get each one (`ADR-0017`; Settings → API
  keys since 2026-10-09 enters them, but does not say where they come
  from);
- the storage paths — where AIStack keeps its data, which disks and
  folders it reads (media, backups), each to be added by hand to the
  `volumes:` of `x-aistack`.

## Decision

Decided by the owner, 2026-10-10, except § 4–6.

### 1. Before the device sync

The installation assistant is part of 2.0: it comes before the test at
David's. The device sync of `ADR-0022` (§ 8 there) comes after the 2.0
release, as agreed on 2026-10-09.

### 2. What it installs or guides

Docker and Docker Compose; Pocket ID; Ollama and a model
(`qwen2.5:3b`, the local fallback of `ai_runtime.yml`); Gotify and
Syncthing. Each but Docker is optional: the assistant says what is
lost without it (sign-in by the local administrator only; no local AI
fallback; no notifications; no device sync).

### 3. A script, then web pages

A script lays the base on the host; the first start in the browser
guides the rest.

### 4. The script: `install.sh`

Run once on the host, as a user with `sudo`; reads, then asks before
changing anything:

1. the system (Debian, Ubuntu, Linux Mint and LMDE — the `apt` family;
   any other system gets the list of what to install, and stops);
2. Docker Engine and the Compose plugin, from Docker's own repository,
   when missing; the user added to the `docker` group;
3. `/srv/aistack` (or the directory given), `docker-compose.yml` and
   `.env.example` of the version installed, `.env` filled with the
   user's ids and the socket's group, `config/`, `data/`, `.env.web`
   (mode 0600);
4. on request, each optional prerequisite, as its own Compose project
   beside AIStack's (`/srv/<name>`), from a file AIStack ships
   (`deploy/prerequisites/<name>/compose.yml`) — Pocket ID, Gotify,
   Syncthing; Ollama natively, with its own installer, then
   `ollama pull qwen2.5:3b`;
5. `docker compose up -d`, then the address of `/setup` on the local
   network.

Never a secret on screen; never anything done without the person's
yes; a second run changes only what is still missing.

### 5. The web pages: `/setup` becomes a guided first start

The read-only list of `ADR-0017` § 4 becomes steps, each saved from the
page, LAN only, before anyone can sign in (an installation token,
shown by the script, opens them):

Every value the installation needs is asked on these pages, one step
after the other, never left to a file to edit (the owner, 2026-10-10:
"il faut que ces informations soient saisies dans l'assistant
d'installation, comme tous les paramètres qui doivent être renseignés
au fur et à mesure").

1. **The host** — its name, the two ports (`instance_config.yml`).
2. **The public address** — the domain name and the reverse proxy
   (Nginx Proxy Manager, or another); the names AIStack and Pocket ID
   answer on (by default `aistack.<domain>` and `id.<domain>`); the
   page then shows the proxy hosts to create, with the port each
   forwards to, and checks that the public address answers.
3. **Signing in** — Pocket ID (address, client id and secret, with the
   procedure to create the client and the `aistack_admins` group) or
   the local administrator only (its password, hashed in the page's
   request, never stored in clear).
4. **Storage** — where the data lives; the disks and folders AIStack
   reads, chosen among the host's mounts (`aistack.host.mounts`); the
   page writes them to `config/volumes.yml` — a Compose override that
   gives each folder to every service, at the same path, read-only —
   which `docker compose` reads with `docker-compose.yml` through
   `COMPOSE_FILE` in `.env` (written by `install.sh`; Compose's
   `include:` cannot add volumes to a service already declared), and
   says the one command that applies them. The host's disks come from
   `install.sh` (`setup/host-mounts`): the container sees only what it
   is given.
5. **API keys** — every key of `api_keys.yml`, each with its procedure:
   where to get it, what to click, what it unlocks; entered as in
   Settings (`secrets/api_keys.json`).
6. **Check** — each prerequisite asked once (Pocket ID's discovery
   document, Ollama's model list, Gotify's test message, Syncthing's
   version), and what is still missing.

### 6. The manual is the procedure

The manual's section *Mise en route d'une nouvelle installation* is
rewritten around the script and the steps: what the person types, what
they see, what each choice changes. At David's, the owner follows it
as written; every place where it was not enough is a defect of 2.0.

## Implementation state

| Part | State |
|---|---|
| § 4 `install.sh` and the shipped prerequisite projects | done — `scripts/install.sh`, `deploy/prerequisites/{pocket-id,gotify,syncthing}` |
| § 5 the guided first start | in progress — the installation token (`install.sh`, `aistack.cli.setup_token`), step 1 (the host) and step 2 (the public address, the proxy hosts to create, the check), step 3 (signing in: the Pocket ID procedure with the four addresses, the client's id and secret, the fallback administrator's password hashed — kept in `secrets/sign_in.json`, 0600, laid over the web process's environment at start) step 4 (storage: the host's disks listed by `install.sh`, other folders typed, `config/volumes.yml`) in `/setup/step/<n>`; steps 5–6 to do |
| § 6 the manual | to do |
| The test at David's | to do — after § 4–6 |

## Consequences

- An installation no longer needs `docker-compose.yml` edited by hand:
  the paths go to `config/volumes.yml`.
- The web application writes declarations during the first start only;
  afterwards, Settings keeps the API keys, and the declarations stay
  files the owner edits.
- AIStack ships Compose files for software it does not own (Pocket ID,
  Gotify, Syncthing): Pocket ID follows its `v2` tag (its project
  publishes one per major version), Gotify and Syncthing the image the
  installation pulls; once installed, their updates go through the Dock
  like any other service.
- The test at David's runs before the 2.0 release: the script fetches
  its files from a tag (`--ref`), and the image it runs must be
  published under a version — a release candidate, decided with the
  release (`OPS-0002`).

## Open Points

- *Answered 2026-10-10:* David's installation has a domain,
  `sarfatti.fr`, and Nginx Proxy Manager for HTTPS — Pocket ID can be
  installed there; the values are entered in the assistant (§ 5.2),
  never written in AIStack's shipped declarations.
- *Answered 2026-10-10:* the installation token lives in the data
  directory (`setup/token`, mode 0600) until the assistant is finished;
  `install.sh` shows the address that carries it, and
  `docker compose exec web python -m aistack.cli.setup_token` shows it
  again (`--new` replaces it, `--reopen` opens a finished assistant).
  The address leaves it in a cookie for `/setup` alone (`HttpOnly`,
  `SameSite=Strict`); each form carries a value derived from it. What
  `install.sh` answered — the host's name and address, the domain, the
  prerequisites installed, never a secret — is `setup/install.env`,
  the pages' first values.
