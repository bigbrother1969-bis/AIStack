SUPPORTED_EXTENSIONS = {
    ".md",
}


EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "archive",
    "reports",
    "exports",
    ".pytest_cache",
}


# The governed heritage lives in `docs/`, plus the repository
# README, which is the entry point an agent boots from.
#
# This is an allow list, not a deny list, and the difference
# matters: a deny list makes every new directory governed
# knowledge by default, and silence is how a 0-byte file, a
# book manuscript and a package README came to be projected as
# Knowledge Artifacts.
INCLUDED_PATHS = (
    "docs",
    "README.md",
)


EXCLUDED_PATHS = (
    "context/bundles",
    "context/published",
    "inbox",
    ".pytest_cache",
    # Working notes about the project, not governed knowledge
    # about it. `NEXT-SESSION-TODO.md` is the case that named
    # the category: STD-0300 was extracted from it on
    # 2026-08-14 precisely because acceptance criteria were
    # sitting in an unowned note.
    #
    # This also covers `docs/99-meta/integration`, the recorded
    # history of an integration already carried out. Verified
    # on 2026-08-21: the three source-transport documents are
    # named as `Source:` by the governed artifacts that
    # absorbed them, and the three patches were applied.
    #
    # Nothing is deleted. These files stay in the repository
    # and in its history; they stop being presented as governed
    # knowledge.
    "docs/99-meta",
)


def matches_path(relative: str, prefix: str) -> bool:
    """
    True when a repository-relative path is the prefix itself
    or lives under it.

    Plain `startswith` would make the prefix `inbox` swallow
    `inboxes/`, and `docs` swallow `docsets/`. A path boundary
    is a boundary.
    """

    return relative == prefix or relative.startswith(
        prefix + "/"
    )
