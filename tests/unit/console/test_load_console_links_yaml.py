from pathlib import Path

import pytest

from aistack.console.yaml import load_console_links_yaml
from aistack.contracts.console_link import ConsoleLink
from aistack.contracts.instance_config import InstanceConfig


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


_INSTANCE = InstanceConfig(
    lan_hostname="GIGABYTE", service_ports={"selection_ui": 8181}
)


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "console_links.yml",
        """
        links:
          - name: Selection UI
            description: Sélection des candidats
            service: selection_ui
            scope: lan
          - name: Cockpit Santé
            description: Score de santé
            url: /health.html
            scope: public
        """,
    )

    links = load_console_links_yaml(path, instance=_INSTANCE)

    assert len(links) == 2
    assert links[0] == ConsoleLink(
        name="Selection UI",
        description="Sélection des candidats",
        url="http://GIGABYTE:8181",
        scope="lan",
    )
    assert links[1].name == "Cockpit Santé"
    assert links[1].scope == "public"


def test_url_is_still_accepted_directly(tmp_path: Path):
    """A public card keeps declaring `url` itself — the resolution
    through `service` is only for the five LAN cards."""

    path = write(
        tmp_path / "console_links.yml",
        "links:\n  - name: Cockpit Santé\n    description: x\n"
        "    url: /health.html\n    scope: public\n",
    )

    links = load_console_links_yaml(path, instance=_INSTANCE)

    assert links[0].url == "/health.html"


def test_declaring_both_url_and_service_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - name: Selection UI\n    description: x\n"
        "    url: http://GIGABYTE:8181\n    service: selection_ui\n"
        "    scope: lan\n",
    )

    with pytest.raises(ValueError, match="declares both url and service"):
        load_console_links_yaml(path, instance=_INSTANCE)


def test_a_path_is_appended_to_the_service_s_address(tmp_path: Path):
    path = write(
        tmp_path / "console_links.yml",
        "links:\n  - name: Découverte réseau\n    description: x\n"
        "    service: selection_ui\n    path: /network-discovery/\n    scope: lan\n",
    )

    links = load_console_links_yaml(path, instance=_INSTANCE)

    assert links[0].url == "http://GIGABYTE:8181/network-discovery/"


def test_a_path_must_start_with_a_slash(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - name: Découverte réseau\n    description: x\n"
        "    service: selection_ui\n    path: network-discovery/\n    scope: lan\n",
    )

    with pytest.raises(ValueError, match="path must start with /"):
        load_console_links_yaml(path, instance=_INSTANCE)


def test_a_path_without_a_service_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - name: Cockpit Santé\n    description: x\n"
        "    url: /health.html\n    path: /x/\n    scope: public\n",
    )

    with pytest.raises(ValueError, match="path without a service"):
        load_console_links_yaml(path, instance=_INSTANCE)


def test_a_service_the_instance_declares_no_port_for_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - name: Time Machine\n    description: x\n"
        "    service: timemachine_ui\n    scope: lan\n",
    )

    with pytest.raises(ValueError, match="no port for 'timemachine_ui'"):
        load_console_links_yaml(path, instance=_INSTANCE)


def test_service_resolves_through_the_real_instance_config_by_default(
    tmp_path: Path,
):
    """No `instance` supplied — the loader falls back to the real,
    declared `instance_config.yml`, the same convention `languages`
    already follows for `default_languages()`."""

    path = write(
        tmp_path / "console_links.yml",
        "links:\n  - name: Selection UI\n    description: x\n"
        "    service: web_lan\n    path: /selection/\n    scope: lan\n",
    )

    links = load_console_links_yaml(path)

    assert links[0].url == "http://GIGABYTE:8186/selection/"


def test_a_definition_missing_the_links_key_is_refused(tmp_path: Path):
    path = write(tmp_path / "empty.yml", "not_links: []\n")

    with pytest.raises(ValueError, match="missing: links"):
        load_console_links_yaml(path)


def test_links_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "links: not-a-list\n")

    with pytest.raises(ValueError, match="must be a list"):
        load_console_links_yaml(path)


def test_an_entry_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "links:\n  - just-a-string\n")

    with pytest.raises(ValueError, match="must be a mapping"):
        load_console_links_yaml(path)


def test_an_entry_missing_name_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - description: x\n    url: http://GIGABYTE:8181\n"
        "    scope: lan\n",
    )

    with pytest.raises(ValueError, match="missing: name"):
        load_console_links_yaml(path)


def test_an_entry_missing_description_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - name: Selection UI\n    url: http://GIGABYTE:8181\n"
        "    scope: lan\n",
    )

    with pytest.raises(ValueError, match="missing: description"):
        load_console_links_yaml(path)


def test_an_entry_missing_both_url_and_service_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - name: Selection UI\n    description: x\n    scope: lan\n",
    )

    with pytest.raises(ValueError, match="missing: url or service"):
        load_console_links_yaml(path)


def test_an_entry_missing_scope_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - name: Selection UI\n    description: x\n"
        "    url: http://GIGABYTE:8181\n",
    )

    with pytest.raises(ValueError, match="missing: scope"):
        load_console_links_yaml(path)


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_console_links_yaml(path)


def test_invalid_yaml_syntax_is_reported_as_a_value_error(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "links: [not, valid,\n")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_console_links_yaml(path)


def test_the_real_console_links_definition_loads():
    """
    `src/aistack/console/definitions/console_links.yml` is not a
    fixture — it is `PLAN-J11`'s own declared v1 scope, the file
    `aistack.cli.console_render` actually reads. Loading it here means
    a typo in the real, hand-written file is caught by the test
    suite, the same discipline
    `test_the_real_health_score_weights_definition_loads` already
    holds.
    """

    repo_root = Path(__file__).resolve().parents[3]

    links = load_console_links_yaml(
        repo_root
        / "src"
        / "aistack"
        / "console"
        / "definitions"
        / "console_links.yml"
    )

    by_name = {link.name: link for link in links}

    assert set(by_name) == {
        "Selection UI",
        "Priorité CPU",
        "Architecture",
        "Cockpit Santé",
        "Découverte réseau",
        "Assistant de pannes",
        "Time Machine",
        "Dock",
    }
    # LAN-only since 2026-09-18: the owner closed every remaining
    # public exception reachable from the console — these two were
    # public over HTTPS (Cloudflare + NPM subdomains) until then.
    # `console_links.yml`'s own header comment keeps the record of
    # the reversal.
    assert by_name["Selection UI"].url == "http://GIGABYTE:8186/selection/"
    assert by_name["Priorité CPU"].url == "http://GIGABYTE:8186/priority/"
    assert by_name["Architecture"].url == "/architecture.html"
    assert by_name["Cockpit Santé"].url == "/health.html"
    # LAN-only, deliberately: never a `https://...persiaut-family.fr`
    # subdomain — this screen writes which SSH usernames get tried
    # against the owner's own LAN (`PLAN-J11` § 11).
    # Inside AIStack's single web application since 2026-10-03
    # (ADR-0012): the LAN listener, under its own prefix.
    assert by_name["Découverte réseau"].url == "http://GIGABYTE:8186/network-discovery/"
    # LAN-only, deliberately — v1 choice, not a security necessity
    # (`claude/PLAN-TROUBLESHOOTING-ASSISTANT-UI-2026-09-18.md`).
    assert by_name["Assistant de pannes"].url == "http://GIGABYTE:8186/troubleshooting/"
    # The last screen in (ADR-0012), on the port it held alone before.
    assert by_name["Time Machine"].url == "http://GIGABYTE:8186/timemachine/"
    # The dock (ADR-0019): governed changes, LAN only.
    assert by_name["Dock"].url == "http://GIGABYTE:8186/dock/"
    # `scope`, added 2026-09-30: the same LAN/public split this file's
    # own header comments already narrated by hand above, now a field
    # `console/html.py` groups cards by.
    for name in (
        "Selection UI",
        "Priorité CPU",
        "Découverte réseau",
        "Assistant de pannes",
        "Time Machine",
    ):
        assert by_name[name].scope == "lan", name
    for name in ("Architecture", "Cockpit Santé"):
        assert by_name[name].scope == "public", name


# --------------------------------------------------------------------
# Localized fields (ADR-0010, 2026-09-27)
# --------------------------------------------------------------------


def _localized(tmp_path: Path) -> Path:
    return write(
        tmp_path / "console_links.yml",
        """
        links:
          - name:
              fr: Cockpit Santé
              en: Health cockpit
            description:
              fr: Score de santé
              en: Health score
            url: /health.html
            scope: public
          - name: Selection UI
            description:
              fr: Sélection des candidats
            url: http://GIGABYTE:8181
            scope: lan
        """,
    )


def test_a_localized_field_is_resolved_for_the_requested_language(tmp_path: Path):
    links = load_console_links_yaml(_localized(tmp_path), lang="en")

    assert links[0].name == "Health cockpit"
    assert links[0].description == "Health score"
    assert links[0].url == "/health.html"


def test_a_plain_string_is_the_same_in_every_language(tmp_path: Path):
    links = load_console_links_yaml(_localized(tmp_path), lang="en")

    assert links[1].name == "Selection UI"


def test_a_language_a_field_lacks_falls_back_to_the_reference(tmp_path: Path):
    links = load_console_links_yaml(_localized(tmp_path), lang="en")

    assert links[1].description == "Sélection des candidats"


def test_no_language_means_the_reference(tmp_path: Path):
    links = load_console_links_yaml(_localized(tmp_path))

    assert links[0].name == "Cockpit Santé"


def test_a_localized_field_without_the_reference_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "console_links.yml",
        "links:\n  - name: {en: Health}\n    description: x\n    url: /health.html\n"
        "    scope: public\n",
    )

    with pytest.raises(ValueError, match="missing the reference language: fr"):
        load_console_links_yaml(path)


def test_an_undeclared_language_code_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "console_links.yml",
        "links:\n  - name: {fr: Santé, eng: Health}\n    description: x\n"
        "    url: /h\n    scope: public\n",
    )

    with pytest.raises(ValueError, match="undeclared language"):
        load_console_links_yaml(path)


def test_the_real_definition_carries_every_declared_language():
    """
    The loader serves the reference when a translation is missing, so
    a card left untranslated would never raise — it would quietly show
    French on the English console. Held here instead.
    """

    import yaml

    from aistack.i18n import default_languages, missing_languages

    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "src" / "aistack" / "console" / "definitions" / "console_links.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    for link in data["links"]:
        for field in ("name", "description"):
            assert missing_languages(link[field], default_languages()) == (), (
                link.get("url") or link.get("service"),
                field,
            )
