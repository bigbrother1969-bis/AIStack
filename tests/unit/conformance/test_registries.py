from pathlib import Path

from aistack.conformance.registries import (
    registered_entries,
    registry_names,
    retrieval_sites,
    take_registry_inventory,
    tracked_sources,
)
from aistack.conformance.registry_serialization import (
    deserialize_registries,
    serialize_registries,
)
from aistack.contracts.registry_inventory import (
    RegisteredEntry,
    RegistryInventory,
    RetrievalSite,
)


ROOT = Path(__file__).parents[3]


# --------------------------------------------------------------------
# Reading the source
# --------------------------------------------------------------------


def test_a_literal_retrieval_is_read_with_its_identifier():

    found = retrieval_sites(
        "def main():\n"
        "    ctx.providers.get('docker').collect()\n",
        "src/aistack/cli/x.py",
        ("providers",),
    )

    assert len(found) == 1
    assert found[0].registry == "providers"
    assert found[0].identifier == "docker"
    assert found[0].site == "src/aistack/cli/x.py:2"
    assert not found[0].in_tests


def test_a_computed_retrieval_is_read_without_one():
    """
    `self.tasks.get(context.request.task_id)`. The site exists and
    its target does not appear in the source, so `identifier` is
    `None` — a retrieval this measurement cannot name, which is a
    different fact from no retrieval at all.
    """

    found = retrieval_sites(
        "task = self.tasks.get(context.request.task_id)\n",
        "src/aistack/kernel/resolution/task_resolver.py",
        ("tasks",),
    )

    assert len(found) == 1
    assert found[0].is_computed


def test_a_component_holding_a_registry_is_read():
    """
    Matched on the attribute name rather than on the whole path.
    `TaskResolver` receives `kernel.registries.tasks` and stores
    it as `self.tasks`, which is the ordinary way a component
    holds a registry; a rule demanding the full expression would
    see none of them.
    """

    found = retrieval_sites(
        "self.tasks.get('rebuild')\n",
        "src/x.py",
        ("tasks",),
    )

    assert [site.identifier for site in found] == ["rebuild"]


def test_a_get_on_something_that_is_not_a_registry_is_ignored():

    found = retrieval_sites(
        "value = self.metadata.get('image')\n"
        "other = payload.get('name')\n",
        "src/x.py",
        ("providers", "tasks"),
    )

    assert found == []


def test_a_site_under_tests_is_marked():

    found = retrieval_sites(
        "ctx.providers.get('docker')\n",
        "tests/unit/test_x.py",
        ("providers",),
    )

    assert found[0].in_tests


def test_the_file_list_comes_from_the_repository():
    """
    `git ls-files`, not a filesystem walk. `find` returned
    `src/aistack/funnel` for five weeks after its files were
    removed — GOV-0002/OS-018 — and a measurement of a directory
    nobody tracks is a measurement of somebody's disk.
    """

    tracked = tracked_sources(ROOT)

    assert tracked is not None
    assert "src/aistack/kernel/bootstrap/providers.py" in tracked
    assert all(name.endswith(".py") for name in tracked)


def test_git_being_unable_to_answer_is_not_an_empty_repository(tmp_path):
    """
    A directory that is not a repository. `None`, not `[]`: a walk
    over zero files would publish *nothing retrieves anything*
    about every registration there is.
    """

    assert tracked_sources(tmp_path) is None

    inventory = take_registry_inventory(tmp_path)

    assert not inventory.measured
    assert inventory.registered == ()
    assert inventory.registries == registry_names()


# --------------------------------------------------------------------
# Composing the Kernel
# --------------------------------------------------------------------


def test_the_registrations_are_read_from_the_bootstrap():
    """
    Composed, not parsed. `create_kernel()` is the only authority
    on what a running AIStack holds, and reading it any other way
    would be a second implementation that could disagree with the
    first.
    """

    entries = registered_entries()

    assert {entry.qualified_name for entry in entries} >= {
        "providers/docker",
        "providers/compose",
    }

    docker = next(
        entry
        for entry in entries
        if entry.qualified_name == "providers/docker"
    )

    assert docker.entry.endswith("DockerProvider")


def test_the_registry_names_come_from_the_kernel_context():
    """
    A registry added to `KernelRegistries` and to nothing else is
    measured from the day it is added. A list restated here would
    be a second declaration of the same knowledge, which is what
    FDN-P-005 forbids and how ARCH-0007 came to name a registry
    that did not exist.
    """

    from aistack.kernel.registries import KernelRegistries

    assert set(registry_names()) == set(
        KernelRegistries.__dataclass_fields__
    )


def test_the_measurement_over_this_repository():
    """
    What was measured, stated so that a silent instrument is
    distinguishable from a clean heritage.

    **The source floor was 490 on 2026-08-28 and broke on
    2026-08-29 — because the repository shrank.** Fourteen
    modules were removed that day: nine capabilities that could
    not be instantiated, two `KnowledgePackage` classes, a
    contract with no implementation, a facade returning its
    argument, and three packages left empty by the rest. 490 →
    485.

    *A floor is a bet that a number only rises, and this one lost
    it the first time the heritage was correctly cleaned. It
    cannot tell **dead code removed** from **an instrument that
    stopped seeing files**, which is the whole reason it exists.*

    So the floor is set well below the current count rather than
    just under it. What it must catch is an inventory that
    collapses — a `git ls-files` that answers nothing, a walk that
    finds one file — and 400 catches that while leaving room for
    the removals this heritage keeps making. **Floors are for
    silence, not for growth.**
    """

    inventory = take_registry_inventory(ROOT)

    assert inventory.measured
    assert inventory.sources >= 400
    assert len(inventory.registered) >= 4
    assert len(inventory.retrievals) >= 5
    assert not inventory.is_partial


# --------------------------------------------------------------------
# Travelling in the projection
# --------------------------------------------------------------------


def sample() -> RegistryInventory:
    return RegistryInventory(
        registries=("providers", "tasks"),
        registered=(
            RegisteredEntry("providers", "docker", "m.DockerProvider"),
        ),
        retrievals=(
            RetrievalSite("providers", "docker", "src/x.py:2"),
            RetrievalSite("tasks", None, "src/y.py:21"),
        ),
        sources=496,
        measured=True,
    )


def test_the_measurement_survives_the_projection():

    restored = deserialize_registries(serialize_registries(sample()))

    assert restored == sample()


def test_a_computed_identifier_survives_as_computed():
    """
    `null` and a missing key would both read as *no identifier*,
    and one of them means *computed*. The key is always written.
    """

    payload = serialize_registries(sample())

    assert payload["retrievals"][1]["identifier"] is None

    restored = deserialize_registries(payload)

    assert restored.retrievals[1].is_computed


def test_a_payload_from_before_the_measurement_restores_as_unmeasured():

    restored = deserialize_registries({"format_version": "1.0"})

    assert not restored.measured
    assert restored.registered == ()


def test_a_registration_into_a_registry_the_context_lacks_is_refused():
    """
    The two halves are measured separately and must agree. A
    registration naming a registry the Kernel Context does not
    carry means one of the two measurements is describing another
    program.
    """

    import pytest

    with pytest.raises(ValueError):
        RegistryInventory(
            registries=("providers",),
            registered=(
                RegisteredEntry("tasks", "rebuild", "m.Task"),
            ),
            measured=True,
        )
