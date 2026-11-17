"""
The Kernel bootstraps from declared registrations (ADR-0027 § 8).

`registrations.yml` names classes by path, so neither an import nor
`mypy` sees a wrong one any more: these tests are what does.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.kernel.bootstrap import create_kernel, load_registrations, register_declared
from aistack.kernel.bootstrap.default import create_kernel as create_default_kernel
from aistack.kernel.bootstrap.registrations import (
    CATALOG_VIEWS,
    DEFAULT_REGISTRATIONS,
    PROVIDERS,
    TASKS,
    Registration,
    resolve_factory,
)


def _declared(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "registrations.yml"
    path.write_text(text, encoding="utf-8")
    return path


def _ids(kind: str) -> set[str]:
    return {entry.identifier for entry in load_registrations() if entry.kind == kind}


def test_the_declared_file_is_the_one_the_package_ships() -> None:
    assert DEFAULT_REGISTRATIONS.name == "registrations.yml"
    assert DEFAULT_REGISTRATIONS.parent.name == "aistack"
    assert DEFAULT_REGISTRATIONS.is_file()


def test_every_declared_factory_resolves_to_a_class() -> None:
    for registration in load_registrations():
        assert isinstance(resolve_factory(registration), type), registration


def test_every_declared_provider_carries_the_provider_identity() -> None:
    """The base contract `Provider`: what the registry holds (ADR-0027 § 9)."""

    for registration in load_registrations():
        if registration.kind == PROVIDERS:
            provider = resolve_factory(registration)
            assert isinstance(provider.provider_id, str) and provider.provider_id, registration
            assert isinstance(provider.provider_name, str) and provider.provider_name, registration


def test_every_provider_a_declared_task_is_built_on_collects() -> None:
    """A Task is built on a `KnowledgeProvider`: the one contract with `collect()`."""

    declared = {entry.identifier: entry for entry in load_registrations() if entry.kind == PROVIDERS}

    for registration in load_registrations():
        if registration.kind == TASKS and registration.provider:
            provider = resolve_factory(declared[registration.provider])
            assert callable(getattr(provider, "collect", None)), registration


def test_a_task_built_on_all_the_providers_is_given_the_registry() -> None:
    kernel = create_kernel()

    task = kernel.registries.tasks.get("health.render")

    assert task._providers is kernel.registries.providers  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("entry", "said"),
    [
        ("all_providers: yes please", "all_providers must be true or false"),
        ("all_providers: true\n    provider: docker", "one provider or on all of them"),
    ],
)
def test_a_task_that_misdeclares_all_providers_is_refused_and_named(
    tmp_path: Path, entry: str, said: str
) -> None:
    path = _declared(
        tmp_path,
        "tasks:\n  - id: x.y\n    factory: aistack.tasks:HealthRenderTask\n    " + entry + "\n",
    )

    with pytest.raises(ValueError) as refusal:
        load_registrations(path)

    assert said in str(refusal.value)


def test_every_declared_catalog_view_builds() -> None:
    for registration in load_registrations():
        if registration.kind == CATALOG_VIEWS:
            assert callable(getattr(resolve_factory(registration), "build", None)), registration


def test_every_declared_task_executes_under_the_identifier_it_declares() -> None:
    for registration in load_registrations():
        if registration.kind == TASKS:
            task = resolve_factory(registration)
            assert callable(getattr(task, "execute", None)), registration
            assert task.task_id == registration.identifier


def test_a_declared_catalog_view_that_names_itself_is_registered_under_that_name() -> None:
    for registration in load_registrations():
        if registration.kind == CATALOG_VIEWS:
            own = getattr(resolve_factory(registration), "view_id", registration.identifier)
            assert own == registration.identifier


def test_the_kernel_registers_what_is_declared_and_nothing_else() -> None:
    kernel = create_kernel()

    assert set(kernel.registries.providers.all()) == _ids(PROVIDERS)
    assert set(kernel.registries.catalog_views.all()) == _ids(CATALOG_VIEWS)
    assert set(kernel.registries.tasks.all()) == _ids(TASKS)
    assert kernel.registries.selection_strategies.all() == {}


def test_what_the_kernel_registered_before_the_file_existed_is_still_registered() -> None:
    """
    The registrations of 2.0.0, when the bootstrap named each class
    itself — and, since, the providers each chain brought to the
    registry when it started asking for them (ADR-0027 § 9).
    """

    kernel = create_default_kernel()

    def registered(registry: object) -> dict[str, str]:
        return {identifier: type(entry).__name__ for identifier, entry in registry.all().items()}  # type: ignore[attr-defined]

    assert registered(kernel.registries.providers) == {
        "docker": "DockerProvider",
        "compose": "ComposeProvider",
        # The health chain.
        "storage": "StorageProvider",
        "backup": "BackupProvider",
        "gpu": "NvidiaGpuProvider",
        # The troubleshooting chain.
        "host": "HostProvider",
    }
    assert registered(kernel.registries.catalog_views) == {
        "music-selection": "MusicSelectionViewEngine",
        "docker-containers": "DockerContainerViewEngine",
        "media-tree": "MediaTreeViewEngine",
    }
    assert registered(kernel.registries.tasks) == {
        "health.render": "HealthRenderTask",
        "architecture.render": "ArchitectureRenderTask",
        "console.render": "ConsoleRenderTask",
        "timemachine.rebuild": "TimeMachineRebuildTask",
        "network_docker.discover": "NetworkDockerDiscoverTask",
        "ai.reason": "AiReasonTask",
        "declarations.observe": "DeclarationsObserveTask",
        "knowledge.integrity": "KnowledgeIntegrityTask",
    }


def test_registrations_are_read_in_the_order_a_task_needs(tmp_path: Path) -> None:
    path = _declared(
        tmp_path,
        "tasks:\n  - id: t\n    factory: m:T\n    provider: p\n"
        "providers:\n  - id: p\n    factory: m:P\n  - id: q\n    factory: m:Q\n",
    )

    assert load_registrations(path) == (
        Registration(kind=PROVIDERS, identifier="p", factory="m:P"),
        Registration(kind=PROVIDERS, identifier="q", factory="m:Q"),
        Registration(kind=TASKS, identifier="t", factory="m:T", provider="p"),
    )


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("- not a mapping\n", "must contain a mapping"),
        ("policies:\n  - id: a\n    factory: m:C\n", "unknown kinds: ['policies']"),
        ("providers: docker\n", "providers must be a list"),
        ("providers:\n  - docker\n", "providers[0] must be a mapping"),
        ("providers:\n  - factory: m:C\n", "providers[0] is missing: id"),
        ("providers:\n  - id: a\n", "providers[0] is missing: factory"),
        ("providers:\n  - id: a\n    factory: m:C\n    provider: b\n", "unknown keys: ['provider']"),
        ("tasks:\n  - id: a\n    factory: m:C\n    engine: b\n", "unknown keys: ['engine']"),
        ("providers: [\n", "not valid YAML"),
    ],
)
def test_a_malformed_declaration_is_refused_and_named(tmp_path: Path, text: str, said: str) -> None:
    with pytest.raises(ValueError) as refusal:
        load_registrations(_declared(tmp_path, text))

    assert said in str(refusal.value)


@pytest.mark.parametrize(
    ("factory", "said"),
    [
        ("aistack.providers.docker.DockerProvider", "is not written module:Class"),
        ("aistack.providers.nowhere:Provider", "cannot import 'aistack.providers.nowhere'"),
        ("aistack.providers.docker:NoSuchProvider", "has no 'NoSuchProvider'"),
    ],
)
def test_a_factory_that_cannot_be_resolved_is_refused_and_named(factory: str, said: str) -> None:
    registration = Registration(kind=PROVIDERS, identifier="docker", factory=factory)

    with pytest.raises(ValueError) as refusal:
        resolve_factory(registration)

    assert "providers 'docker'" in str(refusal.value)
    assert said in str(refusal.value)


def test_a_task_built_on_a_provider_nobody_registered_is_refused(tmp_path: Path) -> None:
    kernel = create_kernel()
    orphan = (
        Registration(
            kind=TASKS,
            identifier="orphan.discover",
            factory="aistack.kernel.bootstrap.registrations:Registration",
            provider="nowhere",
        ),
    )

    with pytest.raises(ValueError) as refusal:
        register_declared(kernel, orphan)

    assert "'orphan.discover'" in str(refusal.value)
    assert "'nowhere', which is not registered" in str(refusal.value)


def test_a_task_built_on_a_provider_that_does_not_collect_is_refused() -> None:
    kernel = create_kernel()
    on_readings = (
        Registration(
            kind=TASKS,
            identifier="storage.discover",
            factory="aistack.tasks:DockerDiscoverTask",
            provider="storage",
        ),
    )

    with pytest.raises(ValueError) as refusal:
        register_declared(kernel, on_readings)

    assert "tasks 'storage.discover'" in str(refusal.value)
    assert "'storage' is registered and does not collect()" in str(refusal.value)


def test_an_identifier_declared_twice_is_refused() -> None:
    kernel = create_kernel()
    again = tuple(entry for entry in load_registrations() if entry.kind == PROVIDERS)[:1]

    with pytest.raises(ValueError, match="already exists"):
        register_declared(kernel, again)
