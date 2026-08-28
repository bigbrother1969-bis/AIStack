from datetime import datetime

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.contracts.registry_inventory import (
    RegisteredEntry,
    RegistryInventory,
    RetrievalSite,
)
from aistack.integrity.checks.unused_registrations import (
    UnusedRegistrationCheck,
)


NOW = datetime(2026, 8, 28, 12, 0, 0)

REGISTRIES = ("providers", "catalog_views", "tasks")


def bundle(inventory=None) -> ContextBundle:
    return ContextBundle(
        id="test-bundle",
        title="Test",
        generated_at=NOW,
        source_commit="abc1234",
        registry_inventory=inventory,
    )


def inventory(
    registered=(),
    retrievals=(),
    *,
    registries=REGISTRIES,
    measured=True,
    unreadable=(),
) -> RegistryInventory:
    return RegistryInventory(
        registries=registries,
        registered=registered,
        retrievals=retrievals,
        sources=496,
        unreadable=unreadable,
        measured=measured,
    )


def registered(registry, identifier, entry="m.Thing"):
    return RegisteredEntry(
        registry=registry, identifier=identifier, entry=entry
    )


def retrieval(registry, identifier, site="m.py:1", in_tests=False):
    return RetrievalSite(
        registry=registry,
        identifier=identifier,
        site=site,
        in_tests=in_tests,
    )


def summaries(findings):
    return [f.summary for f in findings]


def only(findings, fragment):
    matching = [f for f in findings if fragment in f.summary]
    assert len(matching) == 1, summaries(findings)
    return matching[0]


# --------------------------------------------------------------------
# Registered and retrieved by nothing
# --------------------------------------------------------------------


def test_a_registration_nothing_retrieves_is_published():
    """
    GOV-0002/OS-039 and OS-042, in the half that is a registry
    fact: `by-ids` and `music-selection` were registered at
    bootstrap and named by no site.
    """

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registered=(
                    registered("providers", "docker"),
                    registered("catalog_views", "music-selection"),
                ),
                retrievals=(
                    retrieval("providers", "docker"),
                ),
            )
        )
    )

    finding = only(findings, "retrieved by nothing")

    assert finding.affected == 1
    assert finding.total == 2
    assert finding.subjects == (
        "catalog_views/music-selection — m.Thing",
    )


def test_a_registration_a_site_names_is_not_reported():

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registered=(registered("providers", "docker"),),
                retrievals=(retrieval("providers", "docker"),),
            )
        )
    )

    assert not [f for f in findings if "retrieved by nothing" in f.summary]


def test_an_identifier_retrieved_from_another_registry_does_not_count():
    """
    The pair is the fact, not the string. Two registries may hold
    the same identifier, and a check that compared identifiers
    alone would report one of them as consumed because the other
    was.
    """

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registered=(registered("catalog_views", "docker"),),
                retrievals=(retrieval("providers", "docker"),),
            )
        )
    )

    assert only(findings, "retrieved by nothing").subjects == (
        "catalog_views/docker — m.Thing",
    )


# --------------------------------------------------------------------
# A computed identifier is not an absence
# --------------------------------------------------------------------


def test_a_computed_retrieval_excludes_its_registry_from_the_count():
    """
    **The control case.** `self.tasks.get(context.request.task_id)`
    retrieves something this measurement cannot name. Counting
    what that registry holds as unretrieved would assert that the
    site resolves to none of it — which is exactly the confident
    wrong answer GOV-0002/OS-001 keeps recording.
    """

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registered=(
                    registered("tasks", "rebuild"),
                    registered("catalog_views", "music-selection"),
                ),
                retrievals=(
                    retrieval("tasks", None, "task_resolver.py:21"),
                ),
            )
        )
    )

    assert only(findings, "retrieved by nothing").subjects == (
        "catalog_views/music-selection — m.Thing",
    )

    caveat = only(findings, "computed identifier")

    assert caveat.subjects == ("task_resolver.py:21 — tasks",)


def test_the_caveat_is_published_and_not_left_in_a_docstring():
    """
    A count whose exclusions are documented in the source and not
    in the report is a count read as a total. `contract-debt`
    publishes its own caveat for the same reason.
    """

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registered=(registered("tasks", "rebuild"),),
                retrievals=(retrieval("tasks", None),),
            )
        )
    )

    assert [f for f in findings if "computed identifier" in f.summary]


# --------------------------------------------------------------------
# An empty registry
# --------------------------------------------------------------------


def test_a_registry_the_bootstrap_leaves_empty_is_published():
    """
    GOV-0002/OS-041: `TaskResolver` resolves against an empty
    registry, so the Execution Dimension *has nothing to execute*.
    A resolver that cannot succeed is a sharper condition than a
    capability waiting for its consumer, and the subject says
    which of the two this is.
    """

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registered=(registered("providers", "docker"),),
                retrievals=(
                    retrieval("providers", "docker"),
                    retrieval("tasks", None),
                ),
            )
        )
    )

    finding = only(findings, "hold nothing after bootstrap")

    assert finding.affected == 2
    assert finding.total == 3
    assert finding.subjects == (
        "catalog_views — nothing registers it and nothing asks for it",
        "tasks — asked by a retrieval site that cannot succeed",
    )


def test_every_registry_filled_produces_no_finding():

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registries=("providers",),
                registered=(registered("providers", "docker"),),
                retrievals=(retrieval("providers", "docker"),),
            )
        )
    )

    assert findings == []


# --------------------------------------------------------------------
# Tests are not production
# --------------------------------------------------------------------


def test_retrieved_only_by_tests_is_its_own_condition():
    """
    *0 callers, 0 tests* and *0 callers, tests only* are different
    facts, and GOV-0002/OS-041 turns on the difference: it says
    `KernelRuntime.boot()` is called by tests rather than saying
    it is dead.
    """

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registered=(registered("providers", "docker"),),
                retrievals=(
                    retrieval(
                        "providers",
                        "docker",
                        "tests/unit/test_x.py:4",
                        in_tests=True,
                    ),
                ),
            )
        )
    )

    assert not [f for f in findings if "retrieved by nothing" in f.summary]

    assert only(findings, "by nothing that ships").subjects == (
        "providers/docker",
    )


# --------------------------------------------------------------------
# Not measured is not empty
# --------------------------------------------------------------------


def test_a_projection_without_the_measurement_says_so():

    findings = UnusedRegistrationCheck().evaluate(bundle())

    assert len(findings) == 1
    assert "undeclared, not empty" in findings[0].summary
    assert findings[0].severity is IntegritySeverity.OBSERVATION


def test_an_unmeasured_inventory_is_not_read_as_an_empty_heritage():
    """
    The inventory exists and says the walk did not happen — git
    could not list the sources. Reading its empty lists as an
    answer would publish *nothing is registered* about a heritage
    that registers four things.
    """

    findings = UnusedRegistrationCheck().evaluate(
        bundle(inventory(measured=False))
    )

    assert len(findings) == 1
    assert "undeclared, not empty" in findings[0].summary


def test_an_unparsed_source_is_named_and_the_count_is_a_bound():

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registries=("providers",),
                registered=(registered("providers", "docker"),),
                unreadable=(("src/broken.py", "SyntaxError: x"),),
            )
        )
    )

    assert only(findings, "could not be parsed").subjects == (
        "src/broken.py",
    )


# --------------------------------------------------------------------
# The severities are a decision, and they are watched
# --------------------------------------------------------------------


def test_every_finding_is_an_observation():
    """
    Decided 2026-08-28. STD-P-002 puts specification before
    implementation, so a capability registered ahead of its
    consumer is the prescribed order rather than a fault — the
    reasoning that keeps `contract-debt` at `OBSERVATION` over
    thirteen orphan contracts.

    Which registrations are early and which are orphaned is a
    qualification, and GOV-P-001 places it with the owner:
    OS-039, OS-041 and OS-042 are open on that question and none
    of them is closed by this check.
    """

    findings = UnusedRegistrationCheck().evaluate(
        bundle(
            inventory(
                registered=(
                    registered("catalog_views", "music-selection"),
                ),
                retrievals=(retrieval("tasks", None),),
                unreadable=(("src/broken.py", "SyntaxError: x"),),
            )
        )
    )

    assert len(findings) == 4

    for finding in findings:
        assert finding.severity is IntegritySeverity.OBSERVATION
