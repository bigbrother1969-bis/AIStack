from aistack.catalog.docker.assets import DockerRuntimeCatalogBuilder
from aistack.kernel.catalog import Catalog


def observation(
    *containers: dict,
    images: list[dict] | None = None,
    networks: list[dict] | None = None,
    volumes: list[dict] | None = None,
) -> dict:
    return {
        "provider": {"id": "aistack.provider.docker"},
        "collected_at": "2026-08-27T15:00:00+00:00",
        "docker": {
            "containers": list(containers),
            "images": images or [],
            "networks": networks or [],
            "volumes": volumes or [],
        },
    }


def containers_of(catalog: Catalog) -> list:
    return [item for item in catalog.items if item.kind == "container"]


def images_of(catalog: Catalog) -> list:
    return [item for item in catalog.items if item.kind == "image"]


def test_the_builder_returns_a_governed_catalog():
    """
    GOV-0002/OS-042, qualified 2026-08-29: `CatalogView` is the
    Catalog View, and the Docker path is the debt.

    This builder returned a `dict` while its Compose twin
    returned a `Catalog`, and the two sat side by side under
    `aistack/catalog/` returning different kinds of thing. A
    Catalog View Engine takes a `Catalog`; until this returned
    one, no engine could consume the Docker path.
    """

    catalog = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "a", "Names": "one", "Status": "Up 2 hours"})
    )

    assert isinstance(catalog, Catalog)
    assert catalog.catalog_id == "docker-runtime"
    assert catalog.metadata["source_provider"] == "aistack.provider.docker"
    assert catalog.metadata["collected_at"] == "2026-08-27T15:00:00+00:00"


def test_the_four_families_reach_one_catalog_and_keep_their_kind():
    """
    A `Catalog` is flat; the Docker runtime holds four families.
    `CatalogItem.kind` is what a flat list has for saying which
    family an item belongs to — decided 2026-08-29 by the owner.

    **Nothing is dropped.** The alternative readings were four
    catalogs, and one catalog of containers only; the second would
    have left images, networks and volumes ungoverned, which is
    the loss this asserts against.
    """

    catalog = DockerRuntimeCatalogBuilder().build(
        observation(
            {"ID": "c1", "Names": "web", "Image": "nginx:1.27"},
            images=[{"Repository": "nginx", "Tag": "1.27", "ID": "i1"}],
            networks=[{"ID": "n1", "Name": "bridge", "Driver": "bridge"}],
            volumes=[{"Name": "data", "Driver": "local"}],
        )
    )

    kinds = [item.kind for item in catalog.items]

    assert kinds == ["container", "image", "network", "volume"]


def test_the_catalogue_carries_health_beside_the_sentence_it_came_from():
    """
    Until 2026-08-27 the catalogue carried `status` and `state`
    and nothing else, so every consumer wanting health had to
    parse a sentence — which is how the experimenter came to
    default a missing verdict to `healthy` (GOV-0002/OS-035,
    ADR-0009 § 6).

    `status` is kept verbatim beside it. The derived value does
    not replace the observation it was derived from. **Both moved
    into `CatalogItem.metadata` on 2026-08-29 and neither was
    lost**, which is what this asserts across the type change.
    """

    catalog = DockerRuntimeCatalogBuilder().build(
        observation(
            {"ID": "a", "Names": "one", "Status": "Up 2 hours (healthy)"},
            {"ID": "b", "Names": "two", "Status": "Up 3 days"},
        )
    )

    assert [c.metadata["health"] for c in containers_of(catalog)] == [
        "healthy",
        "undeclared",
    ]

    assert containers_of(catalog)[0].metadata["status"] == "Up 2 hours (healthy)"


def test_a_container_the_collection_returned_without_a_status():
    """
    The builder reads with `.get`, so a missing key is a real
    input. It must reach `undeclared` rather than raise or
    default.
    """

    catalog = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "a", "Names": "one"})
    )

    assert containers_of(catalog)[0].metadata["health"] == "undeclared"


def test_the_health_field_is_a_value_and_not_an_enum_member():
    """
    The catalogue is serialised to JSON. A member leaking here
    would export as `ContainerHealth.HEALTHY` or fail the dump,
    depending on the serialiser — the kind of difference nobody
    sees until a consumer reads it.
    """

    catalog = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "a", "Status": "Up 2 hours (healthy)"})
    )

    health = containers_of(catalog)[0].metadata["health"]

    assert type(health) is str
    assert health == "healthy"


def test_a_container_with_no_name_is_kept():
    """
    The retired `DockerSelectionCatalogBuilder` skipped a
    nameless container silently — `if container.get("name")`. A
    catalog that omits what it observed is worse than one
    carrying an ugly identifier, so the runtime id is used
    instead.
    """

    catalog = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "abc123", "Status": "Up 1 hour"})
    )

    assert [c.id for c in containers_of(catalog)] == ["abc123"]


def test_the_catalogue_carries_mounts():
    """
    `STD-0300` VS-1 criterion 1.2 names "published ports and
    mounts" as what a catalog entry must carry. `docker ps
    --format '{{json .}}'` already reports `Mounts` in its raw
    output — the same JSON line `ports` is already read from —
    so this is the same kind of read as `ports`, not a second
    Docker call.
    """

    catalog = DockerRuntimeCatalogBuilder().build(
        observation(
            {
                "ID": "a",
                "Names": "one",
                "Mounts": "config,media",
            }
        )
    )

    assert containers_of(catalog)[0].metadata["mounts"] == "config,media"


def test_a_container_with_no_mounts_reads_as_empty_not_none():
    catalog = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "a", "Names": "one"})
    )

    assert containers_of(catalog)[0].metadata["mounts"] == ""


def test_mounts_are_sorted_regardless_of_docker_s_own_order():
    """
    `STD-0300` VS-1 criterion 1.3 (regeneration determinism) failed
    on its first live execution, 2026-09-04, against GIGABYTE: two
    consecutive `docker ps` calls with no host change rendered the
    same container's `Mounts` string in a different order. Sorting
    here is what makes two observations that differ only in
    Docker's own ordering produce an identical catalog entry.
    """

    first = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "a", "Names": "one", "Mounts": "media,config,backup"})
    )
    second = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "a", "Names": "one", "Mounts": "backup,media,config"})
    )

    assert (
        containers_of(first)[0].metadata["mounts"]
        == containers_of(second)[0].metadata["mounts"]
        == "backup,config,media"
    )


def test_images_sharing_a_docker_id_are_ordered_regardless_of_docker_s_own_order():
    """
    `STD-0300` VS-1 criterion 1.3 failed a second way on the same
    2026-09-04 live run, after the `mounts` fix closed the first:
    two images carrying the same `docker_id` — one image with two
    repository tags — swapped position in the catalog's `images`
    between two `docker images` calls with no host change. Sorting
    by identity is what makes two observations that differ only in
    Docker's own list order produce an identical catalog.
    """

    first = DockerRuntimeCatalogBuilder().build(
        observation(
            images=[
                {"Repository": "ghcr.io/rommapp/romm", "Tag": "latest", "ID": "i1"},
                {"Repository": "rommapp/romm", "Tag": "latest", "ID": "i1"},
            ]
        )
    )
    second = DockerRuntimeCatalogBuilder().build(
        observation(
            images=[
                {"Repository": "rommapp/romm", "Tag": "latest", "ID": "i1"},
                {"Repository": "ghcr.io/rommapp/romm", "Tag": "latest", "ID": "i1"},
            ]
        )
    )

    assert [i.id for i in images_of(first)] == [i.id for i in images_of(second)] == [
        "ghcr.io/rommapp/romm:latest",
        "rommapp/romm:latest",
    ]


def test_every_metadata_value_is_a_string():
    """
    `CatalogItem.metadata` is `dict[str, str]` and the
    observation is whatever the runtime printed. The previous
    builder passed `None` through and the JSON carried `null`;
    a consumer reading `metadata["ports"]` would get `None` where
    the type says `str`.
    """

    catalog = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "a", "Names": "one"})
    )

    values = containers_of(catalog)[0].metadata.values()

    assert all(type(value) is str for value in values)
