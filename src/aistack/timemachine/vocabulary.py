from __future__ import annotations

# Namespaces for `ADR-0011` § 2. `PROV` is the W3C PROV-O namespace.
# `AISTACK` is based on `pyproject.toml`'s `[project.urls] Repository`;
# it is a stable identifier and need not resolve over HTTP.
PROV = "http://www.w3.org/ns/prov#"
AISTACK = "https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack/vocab#"


# --- Core RDF/XSD, cited the same way `PROV` is above ----------------
#
# Shared by the projection (writer) and the Time Machine screen (reader).
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XSD = "http://www.w3.org/2001/XMLSchema#"

RDF_TYPE = f"{RDF}type"
XSD_DATE_TIME = f"{XSD}dateTime"

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
# Bounds of a governed dock change (`ADR-0019` § 6).
PROV_STARTED_AT_TIME = f"{PROV}startedAtTime"
PROV_ENDED_AT_TIME = f"{PROV}endedAtTime"


# --- `aistack:` extensions § *Decision* 2, 3, 5, 7, 9 add ------------

# § 2 — structural containment (network > host > stack > container),
# orthogonal to provenance.
AISTACK_PART_OF = f"{AISTACK}partOf"

# § 2 — an Explication to the subject it explains (not
# `prov:wasDerivedFrom`, which states what it is derived from).
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

# § 7 — an Explication's review position (`Proposed` / `Validated` /
# `Discarded`), distinct from its confidence level.
AISTACK_EXPLICATION_STATUS = f"{AISTACK}explicationStatus"

# § 7 — an Explication's confidence level (`Proposed`, `Declared`, ...).
AISTACK_CONFIDENCE = f"{AISTACK}confidence"

# The action Docker recorded for one event (`"start"`, `"destroy"`,
# `"exec_create"`, ...), in Docker's own vocabulary.
AISTACK_DOCKER_ACTION = f"{AISTACK}dockerAction"

# How many paths a `docker diff` snapshot reported (after mount-path
# filtering), an `XSD_INTEGER`; the paths themselves are not graph facts.
AISTACK_CHANGE_COUNT = f"{AISTACK}changeCount"

# Docker's `sha256:...` image digest (see `aistack.providers.docker
# .identity`), a plain string literal.
AISTACK_IMAGE_DIGEST = f"{AISTACK}imageDigest"

# How many packages a container's inventory reported, an `XSD_INTEGER`;
# the packages themselves are not graph facts.
AISTACK_PACKAGE_COUNT = f"{AISTACK}packageCount"

# Which package manager answered (`"dpkg"`, `"apk"`, or `"none"` when
# none responded), a plain string literal.
AISTACK_PACKAGE_MECHANISM = f"{AISTACK}packageMechanism"

# Links the nearest `docker-packages` entity before an image-digest
# change to the nearest one after it.
AISTACK_UPGRADE_CORRELATES_WITH = f"{AISTACK}upgradeCorrelatesWith"

# The dock's governed changes (`ADR-0019` § 6). `changeOutcome`
# is how the change ended — `applied`, `rolled_back` or `failed`, the
# proposal's own final state; `previousDigest` the registry digest the
# container ran before it, beside `imageDigest` for the one it was
# changed to. Identifiers, plain `Literal`s, like `imageDigest`.
AISTACK_CHANGE_OUTCOME = f"{AISTACK}changeOutcome"
AISTACK_PREVIOUS_DIGEST = f"{AISTACK}previousDigest"

# What changes on the hosts (`ADR-0020`): one entity per event a
# host collector recorded. `hostEventKind` is the collector's own kind
# (`package`, `apt`, `file`, `unit`, `baseline`); `hostAction` what
# happened (`upgrade`, `modified`, `enabled`…); `hostDetail` the
# versions, states or command line — never a file's fingerprint or
# content.
AISTACK_HOST_EVENT_KIND = f"{AISTACK}hostEventKind"
AISTACK_HOST_ACTION = f"{AISTACK}hostAction"
AISTACK_HOST_DETAIL = f"{AISTACK}hostDetail"
