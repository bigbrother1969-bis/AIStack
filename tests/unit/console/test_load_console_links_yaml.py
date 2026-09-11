from pathlib import Path

import pytest

from aistack.console.yaml import load_console_links_yaml
from aistack.contracts.console_link import ConsoleLink


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "console_links.yml",
        """
        links:
          - name: Selection UI
            description: Sélection des candidats
            url: http://GIGABYTE:8181
          - name: Cockpit Santé
            description: Score de santé
            url: /health.html
        """,
    )

    links = load_console_links_yaml(path)

    assert len(links) == 2
    assert links[0] == ConsoleLink(
        name="Selection UI",
        description="Sélection des candidats",
        url="http://GIGABYTE:8181",
    )
    assert links[1].name == "Cockpit Santé"


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
        "links:\n  - description: x\n    url: http://GIGABYTE:8181\n",
    )

    with pytest.raises(ValueError, match="missing: name"):
        load_console_links_yaml(path)


def test_an_entry_missing_description_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - name: Selection UI\n    url: http://GIGABYTE:8181\n",
    )

    with pytest.raises(ValueError, match="missing: description"):
        load_console_links_yaml(path)


def test_an_entry_missing_url_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "links:\n  - name: Selection UI\n    description: x\n",
    )

    with pytest.raises(ValueError, match="missing: url"):
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
    }
    assert by_name["Selection UI"].url == "http://GIGABYTE:8181"
    assert by_name["Priorité CPU"].url == "http://GIGABYTE:8182"
    assert by_name["Architecture"].url == "/architecture.html"
    assert by_name["Cockpit Santé"].url == "/health.html"
