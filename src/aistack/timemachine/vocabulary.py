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
