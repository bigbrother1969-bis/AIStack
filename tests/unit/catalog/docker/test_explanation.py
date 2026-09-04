from aistack.catalog.docker.explanation import explain_docker_catalog
from aistack.kernel.catalog import Catalog, CatalogItem


def catalog(*items: CatalogItem) -> Catalog:
    return Catalog(catalog_id="docker-runtime", title="Docker Runtime Catalog", items=tuple(items))


def container(
    label: str,
    *,
    image: str = "",
    state: str = "",
    ports: str = "",
    mounts: str = "",
) -> CatalogItem:
    return CatalogItem(
        id=label,
        label=label,
        kind="container",
        metadata={
            "image": image,
            "state": state,
            "ports": ports,
            "mounts": mounts,
        },
    )


def test_one_sentence_per_container():
    """
    `STD-0300` VS-1 criterion 1.1 counts entries; this criterion
    (1.4) is about the explanation, not the catalog, but it still
    holds one sentence per container that reads the criterion asks
    for — the same one-to-one shape.
    """

    result = explain_docker_catalog(catalog(container("a"), container("b")))

    assert len(result) == 2


def test_a_sentence_states_exactly_the_observed_fields():
    result = explain_docker_catalog(
        catalog(
            container(
                "jellyfin",
                image="linuxserver/jellyfin:latest",
                state="running",
                ports="8096/tcp -> 0.0.0.0:8096",
                mounts="config,media",
            )
        )
    )

    assert result == (
        "Container 'jellyfin' runs image 'linuxserver/jellyfin:latest', "
        "state 'running', publishing '8096/tcp -> 0.0.0.0:8096', "
        "with mounts 'config,media'.",
    )


def test_an_absent_field_is_stated_as_absence_not_omitted():
    """
    `DockerRuntimeCatalogBuilder` reads an absent Docker field as
    an empty string rather than dropping the key — an observed
    absence, not a missing observation. The explanation carries the
    same distinction: it says there were no published ports rather
    than silently skipping the clause.
    """

    result = explain_docker_catalog(catalog(container("quiet")))

    assert result == (
        "Container 'quiet' runs image 'an unnamed image', "
        "state 'undeclared', publishing 'no published ports', "
        "with mounts 'no mounts'.",
    )


def test_only_containers_are_explained():
    """
    A `Catalog` also carries images, networks and volumes
    (`DockerRuntimeCatalogBuilder`'s own four families). This
    criterion is about a Docker *infrastructure* — what is
    running — which the other three kinds do not answer.
    """

    image_item = CatalogItem(id="nginx:1.27", label="nginx:1.27", kind="image")

    result = explain_docker_catalog(catalog(container("web"), image_item))

    assert len(result) == 1


def test_every_statement_traces_to_a_catalog_field():
    """
    `STD-0300` VS-1 criterion 1.4, read literally: every word this
    function states about a container is a value read from that
    container's own `CatalogItem.metadata` (or a fixed phrase for
    an observed absence) — nothing is invented.
    """

    item = container(
        "sonarr",
        image="lscr.io/linuxserver/sonarr:latest",
        state="running",
        ports="",
        mounts="config",
    )

    sentence = explain_docker_catalog(catalog(item))[0]

    assert item.label in sentence
    assert item.metadata["image"] in sentence
    assert item.metadata["state"] in sentence
    assert item.metadata["mounts"] in sentence
    assert "no published ports" in sentence
