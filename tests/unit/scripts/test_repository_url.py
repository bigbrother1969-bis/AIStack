from pathlib import Path
import importlib.util

import pytest


def _export_module():
    """
    Load the export script as a module.

    It is a script, not a package member, so it is loaded by
    path — the same way the integration test runs it by path.
    """

    root = Path(__file__).parents[3]
    script = root / "scripts" / "export_project_sources.py"

    spec = importlib.util.spec_from_file_location(
        "export_project_sources",
        script,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


EXPORT = _export_module()


@pytest.mark.parametrize(
    "url",
    [
        "https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack.git",
        "git@github.com:bigbrother1969-bis/AIStack.git",
        "https://codeberg.org/bigbrother1969/AISTack.git",
        "ssh://git@codeberg.org:22/bigbrother1969/AISTack.git",
    ],
)
def test_a_public_location_is_publishable(url):

    assert EXPORT.is_publishable_url(url)


@pytest.mark.parametrize(
    "url",
    [
        # what the SPOT host actually produced on 2026-08-21
        "ssh://git@127.0.0.1:2222/fabrice.persiaut/AISTack.git",
        # what the manifest silently reverted to on 2026-08-14
        "http://192.168.1.10:8101/fabrice.persiaut/AIStack.git",
        "ssh://git@10.223.207.2/fabrice.persiaut/AIStack.git",
        "http://172.16.4.9/x.git",
        "http://localhost:3000/x.git",
        "ssh://git@gigabyte.local/srv/aistack.git",
        "git@192.168.1.10:x.git",
    ],
)
def test_a_private_location_is_refused(url):
    """
    A loopback address, a private range or a `.local` name is
    canonical for nobody. It describes the machine that ran the
    export, not where AIStack lives, and publishing it inside a
    bundle both misleads the consumer and discloses internal
    topology.

    This has happened twice: the manifest reverted to
    `192.168.1.10:8101` on 2026-08-14, and every bundle
    generated on the SPOT host carried `127.0.0.1:2222` until
    2026-08-21.
    """

    assert not EXPORT.is_publishable_url(url)


@pytest.mark.parametrize("url", ["", "not a url", "::::"])
def test_an_unparseable_location_is_refused(url):

    assert not EXPORT.is_publishable_url(url)


def test_the_override_wins(monkeypatch):

    monkeypatch.setenv(
        "AISTACK_REPOSITORY_URL",
        "  https://example.org/aistack.git  ",
    )

    assert (
        EXPORT.repository_url()
        == "https://example.org/aistack.git"
    )


CANONICAL = "https://gitea.persiaut-family.fr/fabrice.persiaut/AIStack.git"


def test_the_project_declares_its_own_canonical_location():
    """
    `pyproject.toml` is where a Python project states where it
    lives. Reading it there means every machine produces the
    same `repository_url`, with no per-host configuration — the
    git remote of a given clone may be a tunnel, a loopback or
    a mirror, and none of those is the canonical location.
    """

    assert EXPORT.declared_repository_url() == CANONICAL


def test_the_declaration_beats_the_git_remote(monkeypatch):

    monkeypatch.delenv("AISTACK_REPOSITORY_URL", raising=False)

    assert EXPORT.repository_url() == CANONICAL


def test_the_override_beats_the_declaration(monkeypatch):

    monkeypatch.setenv(
        "AISTACK_REPOSITORY_URL",
        "https://example.org/fork.git",
    )

    assert EXPORT.repository_url() == "https://example.org/fork.git"


def test_a_private_declaration_is_ignored(tmp_path, monkeypatch):
    """
    Declaring it in the repository does not make it publishable.
    The same rule applies wherever the value comes from.
    """

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\n\n'
        '[project.urls]\n'
        'Repository = "http://192.168.1.10:8101/x.git"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(EXPORT, "ROOT", tmp_path)

    assert EXPORT.declared_repository_url() is None


def test_a_missing_declaration_is_not_an_error(tmp_path, monkeypatch):

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\n', encoding="utf-8"
    )

    monkeypatch.setattr(EXPORT, "ROOT", tmp_path)

    assert EXPORT.declared_repository_url() is None
