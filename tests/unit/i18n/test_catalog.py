from pathlib import Path

import pytest

from aistack.i18n import load_catalogs, load_languages_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def two_languages(tmp_path: Path) -> Path:
    return write(
        tmp_path / "languages.yml",
        """
        reference: fr
        languages:
          - code: fr
            name: Français
          - code: en
            name: English
        """,
    )


# --------------------------------------------------------------------
# languages.yml
# --------------------------------------------------------------------


def test_a_complete_language_definition_is_loaded(tmp_path: Path):
    languages = load_languages_yaml(two_languages(tmp_path))

    assert languages.reference == "fr"
    assert languages.codes() == ("fr", "en")
    assert languages.available[1].name == "English"
    assert languages.is_available("en")
    assert not languages.is_available("de")
    assert not languages.is_available(None)


def test_a_reference_that_is_not_declared_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "languages.yml",
        "reference: de\nlanguages:\n  - code: fr\n    name: Français\n",
    )

    with pytest.raises(ValueError, match="reference 'de' is not one of"):
        load_languages_yaml(path)


def test_a_code_declared_twice_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "languages.yml",
        (
            "reference: fr\nlanguages:\n"
            "  - code: fr\n    name: Français\n"
            "  - code: fr\n    name: French\n"
        ),
    )

    with pytest.raises(ValueError, match="declares a code twice"):
        load_languages_yaml(path)


def test_a_language_missing_its_name_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "languages.yml", "reference: fr\nlanguages:\n  - code: fr\n"
    )

    with pytest.raises(ValueError, match="missing: name"):
        load_languages_yaml(path)


def test_a_definition_missing_its_reference_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "languages.yml", "languages:\n  - code: fr\n    name: Français\n"
    )

    with pytest.raises(ValueError, match="missing: reference"):
        load_languages_yaml(path)


def test_an_empty_language_list_is_refused(tmp_path: Path):
    path = write(tmp_path / "languages.yml", "reference: fr\nlanguages: []\n")

    with pytest.raises(ValueError, match="non-empty list"):
        load_languages_yaml(path)


# --------------------------------------------------------------------
# catalogs/<code>/<namespace>.yml
# --------------------------------------------------------------------


def test_nested_messages_are_flattened_under_their_file_stem(tmp_path: Path):
    languages = load_languages_yaml(two_languages(tmp_path))
    root = tmp_path / "catalogs"
    write(root / "fr" / "console.yml", "cartouche:\n  title: État\n")
    write(root / "en" / "console.yml", "cartouche:\n  title: Health\n")

    catalogs = load_catalogs(languages, root)

    assert catalogs["fr"] == {"console.cartouche.title": "État"}
    assert catalogs["en"] == {"console.cartouche.title": "Health"}


def test_a_language_without_a_catalog_directory_is_refused(tmp_path: Path):
    languages = load_languages_yaml(two_languages(tmp_path))
    root = tmp_path / "catalogs"
    write(root / "fr" / "common.yml", "a: b\n")

    with pytest.raises(ValueError, match="no catalog directory for language 'en'"):
        load_catalogs(languages, root)


def test_a_non_string_message_is_refused(tmp_path: Path):
    """`yes` unquoted is a boolean in YAML — refused, never shown as `True`."""

    languages = load_languages_yaml(two_languages(tmp_path))
    root = tmp_path / "catalogs"
    write(root / "fr" / "common.yml", "confirm: yes\n")
    write(root / "en" / "common.yml", "confirm: 'yes'\n")

    with pytest.raises(ValueError, match=r"common\.confirm must be a string"):
        load_catalogs(languages, root)


def test_invalid_yaml_is_reported_as_a_value_error(tmp_path: Path):
    languages = load_languages_yaml(two_languages(tmp_path))
    root = tmp_path / "catalogs"
    write(root / "fr" / "common.yml", "a: [broken,\n")
    write(root / "en" / "common.yml", "a: b\n")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_catalogs(languages, root)


# --------------------------------------------------------------------
# flags — owner's request, 2026-09-27
# --------------------------------------------------------------------


def with_flag(tmp_path: Path, flag: str) -> Path:
    return write(
        tmp_path / "languages.yml",
        f"""
        reference: fr
        languages:
          - code: fr
            name: Français
            flag: {flag}
        """,
    )


def test_a_declared_flag_is_loaded_as_a_data_uri(tmp_path: Path):
    write(tmp_path / "flags" / "fr.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')

    language = load_languages_yaml(with_flag(tmp_path, "fr.svg")).available[0]

    assert language.flag.startswith("data:image/svg+xml;base64,")


def test_a_language_without_a_flag_has_none(tmp_path: Path):
    languages = load_languages_yaml(two_languages(tmp_path))

    assert languages.available[0].flag == ""


def test_a_declared_flag_that_does_not_exist_is_refused(tmp_path: Path):
    # Neither beside the declaration nor among the shipped flags.
    with pytest.raises(ValueError, match="flag file not found"):
        load_languages_yaml(with_flag(tmp_path, "xx.svg"))


def test_a_declaration_copied_elsewhere_keeps_the_shipped_flags(tmp_path: Path):
    assert load_languages_yaml(with_flag(tmp_path, "fr.svg")).available[0].flag.startswith("data:image/svg+xml")


@pytest.mark.parametrize("flag", ["../secret.svg", "fr.png", "sub/fr.svg"])
def test_a_flag_is_a_plain_svg_file_name(tmp_path: Path, flag: str):
    with pytest.raises(ValueError, match=r"flag must be an \.svg file name"):
        load_languages_yaml(with_flag(tmp_path, flag))


def test_every_real_language_declares_a_flag():
    for language in load_languages_yaml().available:
        assert language.flag.startswith("data:image/svg+xml;base64,"), language.code
