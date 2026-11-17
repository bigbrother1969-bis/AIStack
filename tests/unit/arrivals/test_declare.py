from __future__ import annotations

from pathlib import Path

import yaml

from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.arrivals.declare import Outcome, declare_container
from aistack.kernel.bootstrap.default import create_kernel

FILE = """\
# Mes services, à la main.
categories:
  # Intelligence artificielle
  - name: IA
    services:
      - name: Stable Diffusion
        container: sd-a1111
        description: Images

      - name: Ollama
        container: ollama
        description: Modèles locaux
  # Médias
  - name: Médias
    services:
      - name: Jellyfin
        container: jellyfin
"""


def write(tmp_path: Path, text: str = FILE) -> Path:
    path = tmp_path / "service_categorization.yml"
    path.write_text(text, encoding="utf-8")

    return path


def declare(path: Path, **overrides: object) -> Outcome:
    values: dict[str, object] = {
        "name": "KoboldCpp",
        "container": "koboldcpp",
        "description": "Écriture « assistée »",
        "category": "IA",
        "new_category": False,
    }
    values.update(overrides)

    return declare_container(create_kernel().services.transactions, path.parent / "data", path, **values)  # type: ignore[arg-type]


def containers(path: Path) -> dict[str, list[str]]:
    declared = load_service_categorization_yaml(path)

    return {c.name: [s.container or s.name for s in c.services] for c in declared.categories}


def test_the_service_goes_after_the_last_service_of_its_category_and_the_rest_is_untouched(tmp_path: Path):
    path = write(tmp_path)

    assert declare(path) is Outcome.DECLARED

    assert containers(path) == {"IA": ["sd-a1111", "ollama", "koboldcpp"], "Médias": ["jellyfin"]}
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Mes services, à la main.\n")
    assert "  # Médias\n  - name: Médias" in text
    assert text.index("koboldcpp") < text.index("# Médias")
    assert yaml.safe_load(text)["categories"][0]["services"][2]["description"] == "Écriture « assistée »"


def test_a_dated_copy_of_the_previous_file_is_kept(tmp_path: Path):
    path = write(tmp_path)

    declare(path)

    (copy,) = tmp_path.glob("service_categorization.yml.avant-arrivals-*")
    assert copy.read_text(encoding="utf-8") == FILE


def test_a_container_already_declared_changes_nothing(tmp_path: Path):
    path = write(tmp_path)

    assert declare(path, container="ollama") is Outcome.ALREADY
    assert path.read_text(encoding="utf-8") == FILE
    assert not list(tmp_path.glob("*.avant-arrivals-*"))


def test_an_unknown_category_is_refused_unless_a_new_one_is_asked(tmp_path: Path):
    path = write(tmp_path)

    assert declare(path, category="Domotique") is Outcome.NO_CATEGORY
    assert path.read_text(encoding="utf-8") == FILE


def test_a_new_category_is_added_at_the_end(tmp_path: Path):
    path = write(tmp_path)

    assert declare(path, category="Écriture", new_category=True) is Outcome.DECLARED

    assert containers(path)["Écriture"] == ["koboldcpp"]
    assert containers(path)["IA"] == ["sd-a1111", "ollama"]


def test_a_new_category_with_the_name_of_an_existing_one_goes_in_that_one(tmp_path: Path):
    path = write(tmp_path)

    assert declare(path, category="IA", new_category=True) is Outcome.DECLARED
    assert containers(path)["IA"] == ["sd-a1111", "ollama", "koboldcpp"]


def test_the_shipped_empty_file_receives_its_first_category(tmp_path: Path):
    path = write(tmp_path, "# Nothing is declared on a new installation.\n\ncategories: []\n")

    assert declare(path, category="IA", new_category=True) is Outcome.DECLARED
    assert containers(path) == {"IA": ["koboldcpp"]}


def test_a_category_without_services_is_left_to_the_owner(tmp_path: Path):
    text = "categories:\n  - name: IA\n    services: []\n"
    path = write(tmp_path, text)

    assert declare(path) is Outcome.UNSUPPORTED
    assert path.read_text(encoding="utf-8") == text


def test_a_file_that_is_not_the_expected_shape_is_left_alone(tmp_path: Path):
    path = write(tmp_path, "services: []\n")

    assert declare(path, category="IA", new_category=True) is Outcome.UNSUPPORTED
    assert path.read_text(encoding="utf-8") == "services: []\n"


def test_a_blank_name_is_refused(tmp_path: Path):
    path = write(tmp_path)

    assert declare(path, name="  ") is Outcome.INVALID
    assert path.read_text(encoding="utf-8") == FILE


def test_an_indentation_of_four_spaces_is_followed(tmp_path: Path):
    text = "categories:\n    - name: IA\n      services:\n          - name: Ollama\n            container: ollama\n"
    path = write(tmp_path, text)

    assert declare(path) is Outcome.DECLARED
    assert containers(path) == {"IA": ["ollama", "koboldcpp"]}


REFERENCE = Path(__file__).resolve().parents[2] / "reference" / "definitions" / "service_categorization.yml"


def test_the_reference_hosts_own_file_takes_a_service_in_each_of_its_categories(tmp_path: Path):
    """The owner's real file: comments, blank lines and a layout of its own."""

    original = load_service_categorization_yaml(REFERENCE)

    for index, category in enumerate(original.categories):
        path = tmp_path / f"{index}.yml"
        path.write_text(REFERENCE.read_text(encoding="utf-8"), encoding="utf-8")

        assert declare(path, container=f"new-{index}", category=category.name) is Outcome.DECLARED

        after = load_service_categorization_yaml(path)
        assert [c.name for c in after.categories] == [c.name for c in original.categories]
        assert [s.container for s in after.categories[index].services][-1] == f"new-{index}"
        assert sum(len(c.services) for c in after.categories) == sum(len(c.services) for c in original.categories) + 1
