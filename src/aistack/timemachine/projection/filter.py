from __future__ import annotations

from typing import Iterable

from aistack.timemachine.graph import Literal


def is_user_data_path(candidate: str, user_data_roots: Iterable[str]) -> bool:
    """
    `True` if `candidate` names a path under any of `user_data_roots`
    — matches the root itself and anything below it, but never a
    sibling that merely shares its prefix (`"/mnt/nextcloudX"` does
    not match a root of `"/mnt/nextcloud"`).
    """

    for root in user_data_roots:
        stripped = root.rstrip("/")
        if candidate == stripped or candidate.startswith(f"{stripped}/"):
            return True

    return False


def filter_fact(
    subject: str,
    obj: str | Literal,
    user_data_roots: Iterable[str] = (),
) -> bool:
    """
    The projection filter (`ADR-0011` § 6): `True` keeps a fact,
    `False` drops it before it reaches the store. Dropping, not
    masking, since a masked path still reveals that it exists.

    A fact is dropped when its subject, or its IRI object, is a path
    under a user-data root (a Nextcloud or Immich file, never
    configuration or binaries). `Literal` objects are not checked.
    `user_data_roots` is empty by default: no projected stream collects
    users' files yet.
    """

    if is_user_data_path(subject, user_data_roots):
        return False

    if isinstance(obj, str) and is_user_data_path(obj, user_data_roots):
        return False

    return True
