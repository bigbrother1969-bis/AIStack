from pathlib import Path

import pytest

from aistack.architecture.definition import (
    ServiceCategorizationDefinition,
    ServiceCategoryDefinition,
    ServiceDefinition,
)
from aistack.architecture.yaml import load_service_categorization_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_categorization_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "service_categorization.yml",
        """
        categories:
          - name: Administration, Cloud & Utilitaires
            services:
              - name: Nginx Proxy Manager
                container: npm
              - name: Pi-hole
        """,
    )

    definition = load_service_categorization_yaml(path)

    assert isinstance(definition, ServiceCategorizationDefinition)
    assert len(definition.categories) == 1

    category = definition.categories[0]
    assert category.name == "Administration, Cloud & Utilitaires"
    assert len(category.services) == 2

    npm, pihole = category.services
    assert npm.name == "Nginx Proxy Manager"
    assert npm.container == "npm"
    assert pihole.name == "Pi-hole"
    assert pihole.container is None


def test_icon_href_and_description_are_loaded(tmp_path: Path):
    path = write(
        tmp_path / "rich_service.yml",
        """
        categories:
          - name: Supervision
            services:
              - name: Pi-hole
                icon: pi-hole
                href: https://pihole.persiaut-family.fr/admin
                description: Gestionnaire de DNS + Blocage de publicités
        """,
    )

    service = load_service_categorization_yaml(path).categories[0].services[0]
    assert service.icon == "pi-hole"
    assert service.href == "https://pihole.persiaut-family.fr/admin"
    assert service.description == "Gestionnaire de DNS + Blocage de publicités"


def test_icon_href_and_description_default_to_none_when_absent(tmp_path: Path):
    path = write(
        tmp_path / "bare_service.yml",
        """
        categories:
          - name: Supervision
            services:
              - name: LibreSpeed
        """,
    )

    service = load_service_categorization_yaml(path).categories[0].services[0]
    assert service.icon is None
    assert service.href is None
    assert service.description is None


def test_an_empty_icon_href_or_description_value_reads_as_none(tmp_path: Path):
    """
    Same discipline as `container:` present-but-blank — a hand-edit
    slip never travels downstream as an empty string.
    """

    path = write(
        tmp_path / "blank_fields.yml",
        """
        categories:
          - name: Supervision
            services:
              - name: LibreSpeed
                icon:
                href:
                description:
        """,
    )

    service = load_service_categorization_yaml(path).categories[0].services[0]
    assert service.icon is None
    assert service.href is None
    assert service.description is None


def test_multiple_categories_are_loaded_in_source_order(tmp_path: Path):
    """
    Category and service order is the owner's own dashboard order —
    nothing derived from Docker or Compose is sorted against it, the
    opposite discipline from `ComposeRuntimeCatalogBuilder`'s own
    `containers` field.
    """

    path = write(
        tmp_path / "two_categories.yml",
        """
        categories:
          - name: Supervision
            services:
              - name: Beszel
                container: beszel
          - name: Développement
            services:
              - name: Gitea
                container: gitea
        """,
    )

    definition = load_service_categorization_yaml(path)

    assert [c.name for c in definition.categories] == [
        "Supervision",
        "Développement",
    ]


def test_a_service_with_no_container_key_reads_as_none(tmp_path: Path):
    path = write(
        tmp_path / "no_container.yml",
        """
        categories:
          - name: Supervision
            services:
              - name: LibreSpeed
        """,
    )

    service = load_service_categorization_yaml(path).categories[0].services[0]
    assert service.container is None


def test_a_service_with_an_empty_container_value_reads_as_none(tmp_path: Path):
    """
    `container:` present but blank (a hand-edit slip, or a YAML
    `container:` with nothing after it) is the same "no container" as
    the key being absent entirely — never an empty string traveling
    downstream as if it were a real name.
    """

    path = write(
        tmp_path / "blank_container.yml",
        """
        categories:
          - name: Supervision
            services:
              - name: LibreSpeed
                container:
        """,
    )

    service = load_service_categorization_yaml(path).categories[0].services[0]
    assert service.container is None


def test_a_category_with_no_services_is_valid(tmp_path: Path):
    path = write(
        tmp_path / "empty_category.yml",
        """
        categories:
          - name: Empty
            services: []
        """,
    )

    definition = load_service_categorization_yaml(path)
    assert definition.categories[0].services == ()


def test_no_categories_at_all_is_valid(tmp_path: Path):
    path = write(tmp_path / "empty.yml", "categories: []\n")

    assert load_service_categorization_yaml(path).categories == ()


def test_categories_missing_entirely_is_named(tmp_path: Path):
    path = write(tmp_path / "no_key.yml", "unrelated: true\n")

    with pytest.raises(ValueError, match="categories"):
        load_service_categorization_yaml(path)


def test_categories_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(tmp_path / "not_a_list.yml", "categories: Supervision\n")

    with pytest.raises(ValueError, match="categories must be a list"):
        load_service_categorization_yaml(path)


def test_a_category_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "category_not_mapping.yml",
        """
        categories:
          - Supervision
        """,
    )

    with pytest.raises(ValueError, match=r"categories\[0\] must be a mapping"):
        load_service_categorization_yaml(path)


def test_a_category_missing_its_name_is_named_by_position(tmp_path: Path):
    path = write(
        tmp_path / "category_no_name.yml",
        """
        categories:
          - services: []
        """,
    )

    with pytest.raises(ValueError, match=r"categories\[0\].*name"):
        load_service_categorization_yaml(path)


def test_a_category_missing_its_services_is_named_by_position(tmp_path: Path):
    path = write(
        tmp_path / "category_no_services.yml",
        """
        categories:
          - name: Supervision
        """,
    )

    with pytest.raises(ValueError, match=r"categories\[0\].*services"):
        load_service_categorization_yaml(path)


def test_a_categorys_services_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "services_not_list.yml",
        """
        categories:
          - name: Supervision
            services: Beszel
        """,
    )

    with pytest.raises(ValueError, match="services must be a list"):
        load_service_categorization_yaml(path)


def test_a_service_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "service_not_mapping.yml",
        """
        categories:
          - name: Supervision
            services:
              - Beszel
        """,
    )

    with pytest.raises(
        ValueError, match=r"categories\[0\]\.services\[0\] must be a mapping"
    ):
        load_service_categorization_yaml(path)


def test_a_service_missing_its_name_is_named_by_position(tmp_path: Path):
    path = write(
        tmp_path / "service_no_name.yml",
        """
        categories:
          - name: Supervision
            services:
              - container: beszel
        """,
    )

    with pytest.raises(
        ValueError, match=r"categories\[0\]\.services\[0\].*name"
    ):
        load_service_categorization_yaml(path)


def test_the_second_categorys_second_service_is_named_by_its_own_position(
    tmp_path: Path,
):
    path = write(
        tmp_path / "nested_position.yml",
        """
        categories:
          - name: Supervision
            services:
              - name: Beszel
                container: beszel
          - name: Développement
            services:
              - name: Gitea
                container: gitea
              - container: cyberchef
        """,
    )

    with pytest.raises(
        ValueError, match=r"categories\[1\]\.services\[1\].*name"
    ):
        load_service_categorization_yaml(path)


def test_a_categorization_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_service_categorization_yaml(path)


def test_the_real_service_categorization_loads():
    """
    `src/aistack/architecture/definitions/service_categorization.yml`
    is not a fixture — it is the ported classification the graph-
    building step (`PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`, step 3)
    reads. Loading it here means a typo in the real, hand-written
    file is caught by the test suite, the same discipline
    `test_the_real_resource_priority_definition_loads` already applies
    to `resource_priority.yml`.
    """

    repo_root = Path(__file__).resolve().parents[3]

    definition = load_service_categorization_yaml(
        repo_root
        / "src"
        / "aistack"
        / "architecture"
        / "definitions"
        / "service_categorization.yml"
    )

    names = [category.name for category in definition.categories]
    assert names == [
        "Administration, Cloud & Utilitaires",
        "Supervision",
        "Divertissement & Bureau",
        "Téléchargements",
        "AIStack",
        "Développement",
    ]

    all_services = [
        service
        for category in definition.categories
        for service in category.services
    ]
    assert len(all_services) == 69

    by_name = {service.name: service for service in all_services}

    assert by_name["Nginx Proxy Manager"].container == "npm"
    assert by_name["Pi-hole"].container is None
    assert by_name["FreeboxOS"].container is None
    assert by_name["Jellyfin"].container == "jellyfin"
    assert by_name["Music Sync"].container is None
    # 1.6 closure, 2026-10-02: the real catalog showed this runs as a
    # container after all — the 2026-09-10 "no container" porting
    # assumption was wrong, not a provider AIStack still lacks.
    assert by_name["Architecture Homelab"].container == "archi"
    assert by_name["IT-Tools"].container == "it-tools"

    aistack_category = next(
        c for c in definition.categories if c.name == "AIStack"
    )
    assert [s.name for s in aistack_category.services] == ["Music Sync"]

    # 1.6 closure, 2026-10-02: 22 technical/infra entries added to
    # resolve real `discovered_undeclared` inventory gaps — sidecars
    # of an already-declared service, plus two infra tools with no
    # page of their own. Owner's explicit choice: `name`/`container`
    # only, no `icon`/`href` — there is nothing to click on a
    # database or a VPN gateway. Every other, user-facing service
    # keeps the universal icon/href/description invariant this test
    # already held before this closure.
    _NO_ICON_OR_HREF = {
        "Nextcloud — Base de données",
        "Nextcloud — Redis",
        "Nextcloud — Cron",
        "Nextcloud — Collabora",
        "Vikunja — Base de données",
        "Watchtower",
        "Beszel — Agent distant",
        "Scrutiny — Collecteur distant",
        "Immich — Base de données",
        "Immich — Redis",
        "Immich — Machine Learning",
        "Booklore — Base de données",
        "Komf",
        "Paperless — Base de données",
        "Paperless — Redis",
        "Boostack — Base de données",
        "Wordpress — Base de données",
        "EmulatorJS / ROMM — Base de données",
        "Gluetun",
        "Unpackerr",
    }
    assert len(_NO_ICON_OR_HREF) == 20

    # `icon`/`href`/`description` joined 2026-09-12 (§10) — every
    # user-facing service carries all three, unlike `container` (which
    # several legitimately lack). A missing one here is the real file
    # regressing, not a case this loader should tolerate silently.
    for service in all_services:
        if service.name in _NO_ICON_OR_HREF:
            assert service.icon is None, f"{service.name} unexpectedly has an icon"
            assert service.href is None, f"{service.name} unexpectedly has an href"
            assert service.description, f"{service.name} has no description"
            continue

        assert service.icon, f"{service.name} has no icon"
        assert service.href, f"{service.name} has no href"
        assert service.description, f"{service.name} has no description"

    assert by_name["Nginx Proxy Manager"].icon == "nginx-proxy-manager"
    assert by_name["Nginx Proxy Manager"].href == "https://npm.persiaut-family.fr"
    assert (
        by_name["Nginx Proxy Manager"].description
        == "Gestionnaire des Proxy Hosts"
    )
    # `FreeboxOS` and `Freebox Dashboard` share one vendored icon — the
    # source declared `mdi-router-wireless` for both.
    assert by_name["FreeboxOS"].icon == "router-wireless"
    assert by_name["Freebox Dashboard"].icon == "router-wireless"
    # The one dead source reference (`icon: books`, 404 against
    # dashboard-icons) the owner replaced rather than carried forward.
    assert by_name["Legal to Read"].icon == "book-open-page-variant"


def test_dataclasses_default_to_empty_when_built_directly():
    """
    `ServiceCategoryDefinition`/`ServiceCategorizationDefinition` are
    also built directly by code (a test fixture, a future step's own
    default), not only by the loader — both default their collection
    to empty rather than requiring an explicit `()`.
    """

    assert ServiceCategoryDefinition(name="Empty").services == ()
    assert ServiceCategorizationDefinition().categories == ()
    assert ServiceDefinition(name="Standalone").container is None
