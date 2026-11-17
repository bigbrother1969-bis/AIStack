import yaml

from aistack.contracts.undeclared import UNDECLARED


def parse_artifact_frontmatter(
    content: str,
) -> dict:
    """
    Read the metadata an artifact declares about itself.

    This is an observation, not an interpretation: only what
    the artifact states is returned. An absent, malformed or
    unterminated frontmatter yields an empty mapping, never a
    guessed value.
    """

    lines = content.split("\n")

    if not lines or lines[0].strip() != "---":
        return {}

    block = None

    for index in range(1, len(lines)):

        if lines[index].strip() == "---":
            block = "\n".join(lines[1:index])
            break

    if block is None:
        return {}

    try:
        data = yaml.safe_load(block)

    except yaml.YAMLError:
        return {}

    if not isinstance(data, dict):
        return {}

    declared = data.get("artifact")

    if not isinstance(declared, dict):
        return {}

    return declared


def declared_value(
    declared: dict,
    key: str,
) -> str:
    """
    Return a declared metadata value, or the explicit string
    "unknown".

    Per FDN-0003 Article 12, an undeclared value is a governed
    state that must remain visible. It is never replaced by a
    plausible default.
    """

    value = declared.get(key)

    if value is None:
        return UNDECLARED

    text = str(value).strip()

    return text or UNDECLARED
