from __future__ import annotations

import re

import yaml

from aistack.contracts.lifecycle import LifecycleDeclaration, LifecycleRegister


BLOCK = re.compile(r"^```lifecycle[ \t]*\n(.*?)^```", re.S | re.M)

DECLARED_FIELDS = frozenset({"container", "expected", "reason"})


class RegisterError(ValueError):
    """
    A governed document does not declare a readable lifecycle
    register.

    Mirrors `CatalogueError` deliberately: same parsing shape, same
    two call sites (an integrity check at projection, a diagnostic
    at runtime), same reason for existing — `ADR-0009` § 4 applies
    to any policy read out of a fenced block in a governed document,
    not only to signatures.
    """


def read_lifecycle_register(document: str) -> LifecycleRegister:
    """
    Read the lifecycle declarations one governed document carries.

    The tag is `lifecycle` and not `yaml`, for the same reason
    `signatures` is not: a document explaining its own format will
    eventually contain an illustrative `yaml` block, and a parser
    taking the first fence found would one day take the wrong one.
    Exactly one `lifecycle` block is allowed, for the same reason
    exactly one `signatures` block is — two would give the document
    two registers and no way to say which governs.
    """

    blocks = BLOCK.findall(document)

    if not blocks:
        raise RegisterError(
            "no ```lifecycle block: the document declares no "
            "register a program can read"
        )

    if len(blocks) > 1:
        raise RegisterError(
            f"{len(blocks)} ```lifecycle blocks: one document "
            "declares one register, or none governs"
        )

    try:
        data = yaml.safe_load(blocks[0])
    except yaml.YAMLError as error:
        raise RegisterError(
            f"the lifecycle block is not valid YAML: {error}"
        ) from error

    if not isinstance(data, dict):
        raise RegisterError(
            "the lifecycle block declares an artifact and its "
            f"declarations; it holds {type(data).__name__}"
        )

    unknown = set(data) - {"artifact", "declarations"}

    if unknown:
        raise RegisterError(
            f"unknown key(s) in the lifecycle block: {sorted(unknown)}"
        )

    artifact = data.get("artifact")

    if not isinstance(artifact, str):
        raise RegisterError(
            "the lifecycle block declares the artifact that owns "
            "it; a grounded finding cites a declaration through "
            "that identifier"
        )

    declared = data.get("declarations") or []

    if not isinstance(declared, list):
        raise RegisterError(
            f"`declarations` is a list; it holds {type(declared).__name__}"
        )

    try:
        return LifecycleRegister(
            artifact=artifact,
            declarations=tuple(
                _declaration(entry, position, artifact)
                for position, entry in enumerate(declared, start=1)
            ),
        )
    except ValueError as error:
        # `LifecycleRegister.__post_init__` raises a plain
        # `ValueError` for a duplicate container — a contract-level
        # invariant, not a parsing error. Wrapped here so every
        # failure this function can produce is the same type,
        # rather than the caller needing to catch two.
        raise RegisterError(str(error)) from error


def _declaration(entry, position: int, artifact: str) -> LifecycleDeclaration:

    where = f"declaration #{position} of {artifact}"

    if not isinstance(entry, dict):
        raise RegisterError(f"{where} is {type(entry).__name__}, not a mapping")

    unknown = set(entry) - DECLARED_FIELDS

    if unknown:
        raise RegisterError(
            f"{where} declares unknown field(s): {sorted(unknown)}"
        )

    try:
        return LifecycleDeclaration(**entry)
    except TypeError as error:
        raise RegisterError(f"{where}: {error}") from error
    except ValueError as error:
        raise RegisterError(f"{where}: {error}") from error
