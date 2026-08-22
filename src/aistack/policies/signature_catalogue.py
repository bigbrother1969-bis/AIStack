from __future__ import annotations

import re

import yaml

from aistack.contracts.signature import Signature, SignatureCatalogue


BLOCK = re.compile(r"^```signatures[ \t]*\n(.*?)^```", re.S | re.M)

DECLARED_FIELDS = frozenset(
    {
        "identifier",
        "pattern",
        "case_sensitive",
        "applies_to",
        "interpretation",
        "remediation",
        "depth",
        "confidence",
        "grounding",
    }
)


class CatalogueError(ValueError):
    """
    A governed document does not declare a readable catalogue.

    This is raised at projection, where it becomes a blocking
    integrity finding and stops a publication, and at runtime,
    where it stops a diagnostic. One parser, two call sites,
    ADR-0009 § 4 — so a document that a check accepted cannot
    fail later in a container.
    """


def read_signature_catalogue(document: str) -> SignatureCatalogue:
    """
    Read the signatures a governed document declares.

    The block is tagged `signatures` rather than `yaml` on
    purpose. A document explaining its own format will sooner or
    later contain an illustrative `yaml` block, and a parser that
    took the first fence it found would eventually take the wrong
    one.

    Exactly one such block is allowed. Two would give one
    document two catalogues and no way to say which governs.

    Every error message names what is wrong and where, because
    the first reader of these messages is whoever edited the
    document and stopped a publication.
    """

    blocks = BLOCK.findall(document)

    if not blocks:
        raise CatalogueError(
            "no ```signatures block: the document declares no "
            "catalogue a program can read"
        )

    if len(blocks) > 1:
        raise CatalogueError(
            f"{len(blocks)} ```signatures blocks: one document "
            "declares one catalogue, or none governs"
        )

    try:
        data = yaml.safe_load(blocks[0])
    except yaml.YAMLError as error:
        raise CatalogueError(
            f"the signatures block is not valid YAML: {error}"
        ) from error

    if not isinstance(data, dict):
        raise CatalogueError(
            "the signatures block declares an artifact and its "
            f"signatures; it holds {type(data).__name__}"
        )

    unknown = set(data) - {"artifact", "signatures"}

    if unknown:
        raise CatalogueError(
            f"unknown key(s) in the signatures block: {sorted(unknown)}"
        )

    artifact = data.get("artifact")

    if not isinstance(artifact, str):
        raise CatalogueError(
            "the signatures block declares the artifact that owns "
            "it; findings cite signatures through that identifier"
        )

    declared = data.get("signatures") or []

    if not isinstance(declared, list):
        raise CatalogueError(
            f"`signatures` is a list; it holds "
            f"{type(declared).__name__}"
        )

    return SignatureCatalogue(
        artifact=artifact,
        signatures=tuple(
            _signature(entry, position, artifact)
            for position, entry in enumerate(declared, start=1)
        ),
    )


def _signature(entry, position: int, artifact: str) -> Signature:

    where = f"signature #{position} of {artifact}"

    if not isinstance(entry, dict):
        raise CatalogueError(
            f"{where} is {type(entry).__name__}, not a mapping"
        )

    unknown = set(entry) - DECLARED_FIELDS

    if unknown:
        raise CatalogueError(
            f"{where} declares unknown field(s): {sorted(unknown)}"
        )

    declared = dict(entry)

    # YAML reads a sequence as a list, and `Signature` is frozen.
    # A list inside a frozen dataclass is a declaration that
    # asserts a protection and delivers none, so the conversion
    # happens here, at the one place where YAML enters, rather
    # than being tolerated by the contract.
    if "applies_to" in declared:
        states = declared["applies_to"]

        if not isinstance(states, list):
            raise CatalogueError(
                f"{where} declares `applies_to` as "
                f"{type(states).__name__}; it is a list of subject "
                f"states, or [\"any\"]"
            )

        declared["applies_to"] = tuple(states)

    try:
        return Signature(**declared)
    except TypeError as error:
        # A missing field. The dataclass says which; this says
        # which signature, which the reader of a failed
        # publication needs more.
        raise CatalogueError(f"{where}: {error}") from error
    except ValueError as error:
        raise CatalogueError(f"{where}: {error}") from error
