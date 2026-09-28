from __future__ import annotations

# `ADR-0011` § *Decision* 2 names a `prov:` prefix and four `aistack:`
# predicates/classes it adds to PROV-O; neither section fixes the
# actual IRIs behind either prefix — a prefix is not itself an
# identifier RDF can resolve. The two constants below are what this
# module grounds them in:
#
# `PROV` is the W3C's own, already-published namespace
# (<https://www.w3.org/TR/prov-o/>) — not a choice, a citation.
#
# `AISTACK` has no external standard to cite, so it is grounded in the
# one real, already-declared identity this project has:
# `pyproject.toml`'s own `[project.urls] Repository`, the SPOT this
# whole heritage already treats as canonical. It does not need to
# resolve to anything over HTTP — most RDF vocabulary namespaces,
# `prov:` included, are identifiers first and dereferenceable pages
# second — it needs to be stable and to belong to this project rather
# than an invented placeholder domain.
PROV = "http://www.w3.org/ns/prov#"
AISTACK = "https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack/vocab#"


# --- Core RDF/XSD, cited the same way `PROV` is above ----------------
#
# Not `ADR-0011`'s own vocabulary — `rdf:type` and `xsd:dateTime` are
# RDF/XSD itself, needed by any writer or reader that touches this
# store at all (`aistack.timemachine.projection` writes both; a
# browsing screen over the graph reads both back). Named once, here,
# rather than redeclared as a private constant in every module that
# needs one — `RDF_TYPE`/`XSD_DATE_TIME` moved here from
# `aistack.timemachine.projection`'s own module scope 2026-09-27, the
# same day `aistack.timemachine.iri` was split out for the same
# reason (one shared place, not one per caller).
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XSD = "http://www.w3.org/2001/XMLSchema#"

RDF_TYPE = f"{RDF}type"
XSD_DATE_TIME = f"{XSD}dateTime"

# Added 2026-09-28 alongside `aistack.timemachine.projection
# .docker_diff` — this heritage's first typed numeric literal
# (`AISTACK_CHANGE_COUNT`, below). Every literal before it was either
# a plain string or `XSD_DATE_TIME`; no predicate needed a magnitude
# before this one.
XSD_INTEGER = f"{XSD}integer"


# --- PROV-O classes and predicates § *Decision* 2 names -------------

PROV_ENTITY = f"{PROV}Entity"
PROV_ACTIVITY = f"{PROV}Activity"
PROV_AGENT = f"{PROV}Agent"

PROV_WAS_GENERATED_BY = f"{PROV}wasGeneratedBy"
PROV_USED = f"{PROV}used"
PROV_WAS_DERIVED_FROM = f"{PROV}wasDerivedFrom"
PROV_WAS_REVISION_OF = f"{PROV}wasRevisionOf"
PROV_WAS_ASSOCIATED_WITH = f"{PROV}wasAssociatedWith"
PROV_WAS_ATTRIBUTED_TO = f"{PROV}wasAttributedTo"
PROV_GENERATED_AT_TIME = f"{PROV}generatedAtTime"
PROV_INVALIDATED_AT_TIME = f"{PROV}invalidatedAtTime"


# --- `aistack:` extensions § *Decision* 2, 3, 5, 7, 9 add ------------

# § 2 — structural containment (network > host > stack > container),
# orthogonal to provenance.
AISTACK_PART_OF = f"{AISTACK}partOf"

# § 2 — an Explication's own `prov:Entity` to the subject it explains;
# deliberately not `prov:wasDerivedFrom`, which already states that an
# explanation is derived from its context — this states, separately,
# what it explains.
AISTACK_EXPLAINS = f"{AISTACK}explains"

# § 3 — a subject's declared, stable identity (a Compose
# `project/service` name, or an explicitly declared name for anything
# Compose does not cover) — never a Docker id, which recreation
# always changes.
AISTACK_STABLE_SUBJECT = f"{AISTACK}stableSubject"

# § 9 — a declared gap in what a collector observed, distinct from an
# absent fact nothing ever claimed to collect.
AISTACK_COLLECTION_GAP = f"{AISTACK}collectionGap"

# § 4 — the bitemporal model's second timestamp: when a fact's subject
# actually occurred, where a collector can state that independently of
# `prov:generatedAtTime` (recording time). Left unstated, never copied
# from `generatedAtTime`, where a collector cannot.
AISTACK_OCCURRED_AT = f"{AISTACK}occurredAt"

# § 5 — the clock a contributing host declares its timestamps against
# (e.g. `"GIGABYTE:systemd-timesyncd"`), reserved so drift is a
# measured fact, not an assumption two hosts' timestamps can be
# compared without one.
AISTACK_CLOCK_SOURCE = f"{AISTACK}clockSource"

# § 7 — an Explication's workflow position (`Proposed` / `Validated` /
# `Discarded`), distinct from `confidence`: `STD-0100`'s scale
# describes epistemic strength, this describes where in a human
# review an Explication currently sits.
AISTACK_EXPLICATION_STATUS = f"{AISTACK}explicationStatus"

# § 7 — an Explication's own `STD-0100` confidence level (`Proposed`
# today; `Declared` or above once a human becomes its author too).
# Not needed by the four existing streams, which state no confidence
# of their own — added alongside the Explications projection that is
# this predicate's first real caller.
AISTACK_CONFIDENCE = f"{AISTACK}confidence"

# 1.5, added 2026-09-28 alongside `aistack.timemachine.projection
# .docker_events` — the action Docker itself recorded for one event
# (`"start"`, `"destroy"`, `"exec_create"`, ...). PROV-O has
# `prov:Activity` for "something that occurred" but no predicate for
# *which kind* of occurrence one Entity represents; the four existing
# streams never needed one (their own Entity is always "an
# observation was recorded", one kind, needing no further label).
# A `docker events` fact is different by its own nature — a container
# lifecycle stream is exactly the sequence of these labels — so this
# names Docker's own vocabulary directly rather than inventing a
# closed enum this project would then have to keep in sync with
# Docker's own.
AISTACK_DOCKER_ACTION = f"{AISTACK}dockerAction"

# 1.5, added 2026-09-28 alongside `aistack.timemachine.projection
# .docker_diff` — how many filesystem paths a `docker diff` snapshot
# reported (after this collector's own mount-path filtering), typed
# `XSD_INTEGER` since it is a magnitude, not an identifier. The full
# path list is deliberately not promoted to individual graph facts —
# see that module's own docstring for why — so this is the one
# lightweight signal the graph gets from a snapshot beyond "it
# happened, for this subject, at this instant."
AISTACK_CHANGE_COUNT = f"{AISTACK}changeCount"

# 1.5, added 2026-09-28 alongside `aistack.timemachine.projection
# .docker_digest` — 1.5's third collector (dérive du digest). A plain
# string literal (Docker's own `sha256:...` configuration digest,
# `aistack.providers.docker.identity`'s own comment explains exactly
# which one), not a new `XSD_INTEGER`-like type: unlike
# `aistack:changeCount`, this is an identifier, never a magnitude, the
# same reasoning `aistack:stableSubject` itself already holds for a
# `Literal` with no `datatype=` given.
AISTACK_IMAGE_DIGEST = f"{AISTACK}imageDigest"

# 1.5.1, added 2026-09-28 alongside `aistack.timemachine.projection
# .docker_packages` — 1.5's fourth and last named collector
# (inventaire des paquets), deferred past 1.5.0 (`ADR-0011` § 22's own
# closing note) and shipped here. How many packages a `docker exec`
# inventory reported for one subject, typed `XSD_INTEGER` for the same
# reason `aistack:changeCount` already is: a magnitude, not an
# identifier. The full name/version list is deliberately not promoted
# to individual graph facts — the same reasoning `aistack.timemachine
# .projection.docker_diff`'s own module comment already gives for
# `aistack:changeCount`, doubled here: a package inventory can hold
# not hundreds but potentially thousands of entries, reachable through
# `aistack.cli.history_query` the same way any other stream's raw
# content already is.
AISTACK_PACKAGE_COUNT = f"{AISTACK}packageCount"

# 1.5.1, same cadrage — which mechanism actually answered this
# subject's own inventory (`"dpkg"`, `"apk"`, or `"none"` — no known
# package manager responded; `aistack.providers.docker.packages`'s own
# module comment explains why this is itself recorded as a fact,
# never collapsed into an empty `packages` list). A plain string
# literal, the same reasoning `aistack:imageDigest` already holds for
# a label rather than a magnitude — not a closed enum this project
# would have to keep in sync with every future base image family, the
# same restraint `aistack:dockerAction` already holds by naming
# Docker's own vocabulary directly rather than inventing one.
AISTACK_PACKAGE_MECHANISM = f"{AISTACK}packageMechanism"
