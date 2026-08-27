from aistack.catalog.docker.assets import DockerRuntimeCatalogBuilder


def observation(*containers: dict) -> dict:
    return {
        "provider": {"id": "aistack.provider.docker"},
        "collected_at": "2026-08-27T15:00:00+00:00",
        "docker": {
            "containers": list(containers),
            "images": [],
            "networks": [],
            "volumes": [],
        },
    }


def containers_of(catalogue: dict) -> list[dict]:
    return catalogue["infrastructure_assets"]["containers"]


def test_the_catalogue_carries_health_beside_the_sentence_it_came_from():
    """
    Until 2026-08-27 the catalogue carried `status` and `state`
    and nothing else, so every consumer wanting health had to
    parse a sentence — which is how the experimenter came to
    default a missing verdict to `healthy` (GOV-0002/OS-035,
    ADR-0009 § 6).

    `status` is kept verbatim beside it. The derived value does
    not replace the observation it was derived from.
    """

    catalogue = DockerRuntimeCatalogBuilder().build(
        observation(
            {"ID": "a", "Names": "one", "Status": "Up 2 hours (healthy)"},
            {"ID": "b", "Names": "two", "Status": "Up 3 days"},
        )
    )

    assert [c["health"] for c in containers_of(catalogue)] == [
        "healthy",
        "undeclared",
    ]

    assert containers_of(catalogue)[0]["status"] == "Up 2 hours (healthy)"


def test_a_container_the_collection_returned_without_a_status():
    """
    The builder reads with `.get`, so a missing key is a real
    input. It must reach `undeclared` rather than raise or
    default.
    """

    catalogue = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "a", "Names": "one"})
    )

    assert containers_of(catalogue)[0]["health"] == "undeclared"


def test_the_health_field_is_a_value_and_not_an_enum_member():
    """
    The catalogue is serialised to JSON. A member leaking here
    would export as `ContainerHealth.HEALTHY` or fail the dump,
    depending on the serialiser — the kind of difference nobody
    sees until a consumer reads it.
    """

    catalogue = DockerRuntimeCatalogBuilder().build(
        observation({"ID": "a", "Status": "Up 2 hours (healthy)"})
    )

    health = containers_of(catalogue)[0]["health"]

    assert type(health) is str
    assert health == "healthy"
