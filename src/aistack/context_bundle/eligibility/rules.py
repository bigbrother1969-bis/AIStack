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


EXCLUDED_PATHS = {
    "context/bundles",
    "context/published",
    "inbox",
    ".pytest_cache",
    # The recorded history of an integration already carried out.
    # Verified on 2026-08-21: the three source-transport documents
    # are named as `Source:` by the governed artifacts that
    # absorbed them, the three patches were applied — the AI
    # protocol one is now FDN-0009 § Uncertainty in Collaboration —
    # and the C1 glossary patch matches FDN-0002 at 93 %.
    #
    # The files stay in the repository. Excluding them from the
    # projection stops the bundle from presenting a transit record
    # as governed knowledge; it deletes nothing.
    "docs/99-meta/integration",
}
