from abc import ABC, abstractmethod
from typing import Protocol

from aistack.conformance.structural import (
    incompatible_members,
    missing_members,
    protocol_members,
    satisfies,
)


# --------------------------------------------------------------------
# Fixtures declared here rather than borrowed from the product.
#
# STD-0002: a test states its own subject. Borrowing a real
# contract would make these results move whenever that contract
# moved, and a conformance checker whose own tests drift is worth
# nothing.
# --------------------------------------------------------------------


class Store(Protocol):
    def get(self, key: str) -> object: ...
    def __contains__(self, key: str) -> bool: ...


class WritableStore(Store, Protocol):
    def put(self, key: str, value: object) -> None: ...


class Check(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, subject: object) -> list:
        raise NotImplementedError


# --------------------------------------------------------------------
# What a contract requires
# --------------------------------------------------------------------


def test_a_contract_requires_the_names_it_declares():

    assert protocol_members(Store) == {"get", "__contains__"}


def test_a_dunder_that_is_part_of_the_contract_is_required():
    """
    `__contains__` is a real member with a real call shape. A
    checker that filtered names by a leading underscore would
    declare a store conformant without ever looking at how
    membership is tested.
    """

    assert "__contains__" in protocol_members(Store)


def test_inherited_members_are_required_too():
    """
    `WritableStore` extends `Store`, so it requires three members.
    Reading only its own namespace reports one, and a checker that
    under-reports what a contract demands is the failure it was
    written to catch.
    """

    assert protocol_members(WritableStore) == {
        "get",
        "__contains__",
        "put",
    }


def test_protocol_machinery_is_not_mistaken_for_a_requirement():
    """
    `__module__`, `_is_protocol`, `__parameters__` and the rest
    are carried by every Protocol. The noise set is measured from
    two empty Protocols rather than listed, because that list
    changes between Python versions.
    """

    assert not {
        name for name in protocol_members(Store) if name.startswith("_")
    } - {"__contains__"}


def test_an_abc_contract_is_read_the_same_way():
    """
    Seven integrity checks implement an ABC, not a Protocol. A
    checker that only understood Protocols would report them all
    as orphans — which is exactly the wrong measurement one
    earlier pass produced.
    """

    assert protocol_members(Check) == {"name", "evaluate"}


class Described(Protocol):
    provider_id: str
    provider_name: str

    def get(self, key: str) -> object: ...


# --------------------------------------------------------------------
# An annotated attribute is a requirement
# --------------------------------------------------------------------


def test_an_annotated_attribute_is_a_required_name():
    """
    `class Provider(Protocol): provider_id: str` puts nothing in
    `vars()` but the `__annotations__` mapping. Reading `vars()`
    alone reports that the contract requires `__annotations__`
    and nothing else — a name every class in the package has.

    Measured on the real package 2026-08-22: `Provider` was
    reported satisfied by all 144 concrete classes. The error
    under-declares the debt, which is the direction that matters.
    """

    assert protocol_members(Described) == {
        "provider_id",
        "provider_name",
        "get",
    }


def test_the_annotations_mapping_is_never_itself_a_requirement():

    assert "__annotations__" not in protocol_members(Described)


def test_a_class_lacking_an_annotated_attribute_does_not_satisfy():

    class NoIdentity:
        def get(self, key: str) -> object:
            return None

    assert not satisfies(Described, NoIdentity)
    assert missing_members(Described, NoIdentity) == {
        "provider_id",
        "provider_name",
    }


def test_an_annotated_attribute_is_compared_on_presence_only():
    """
    The contract names the attribute and gives no value to
    compare against. Presence is the whole requirement; a checker
    that tried to compare call shapes here would raise on a
    member the contract never defined.
    """

    class Identified:
        provider_id = "aistack.provider.docker"
        provider_name = "Docker"

        def get(self, key: str) -> object:
            return None

    assert satisfies(Described, Identified)
    assert incompatible_members(Described, Identified) == {}


# --------------------------------------------------------------------
# Whether an implementation satisfies it
# --------------------------------------------------------------------


def test_a_faithful_implementation_satisfies_the_contract():

    class Faithful:
        def get(self, key: str) -> object:
            return None

        def __contains__(self, key: str) -> bool:
            return False

    assert satisfies(Store, Faithful)
    assert missing_members(Store, Faithful) == set()
    assert incompatible_members(Store, Faithful) == {}


def test_a_missing_member_is_named():

    class Partial:
        def get(self, key: str) -> object:
            return None

    assert not satisfies(Store, Partial)
    assert missing_members(Store, Partial) == {"__contains__"}


def test_a_different_arity_is_refused():
    """
    The case `isinstance` cannot catch. These Protocols are not
    `runtime_checkable`, and making them so would compare names
    without looking at call shapes.
    """

    class WrongArity:
        def get(self, key: str, default: object) -> object:
            return default

        def __contains__(self, key: str) -> bool:
            return False

    assert not satisfies(Store, WrongArity)
    assert "get" in incompatible_members(Store, WrongArity)


def test_a_different_parameter_name_is_refused():
    """
    The contract declares `key`, so the name is part of it. A
    caller writing `store.get(key=...)` would break against an
    implementation that named it otherwise.
    """

    class Renamed:
        def get(self, identifier: str) -> object:
            return None

        def __contains__(self, key: str) -> bool:
            return False

    assert not satisfies(Store, Renamed)
    assert "parameter name differs" in incompatible_members(
        Store, Renamed
    )["get"]


def test_a_positional_only_parameter_may_be_renamed():
    """
    A contract that does not care about the name says so in the
    language rather than in a comment.
    """

    class Loose(Protocol):
        def get(self, key: str, /) -> object: ...

    class Renamed:
        def get(self, whatever: str, /) -> object:
            return None

    assert satisfies(Loose, Renamed)


def test_a_value_where_the_contract_declares_a_callable_is_refused():

    class Attribute:
        get = "not callable"

        def __contains__(self, key: str) -> bool:
            return False

    assert not satisfies(Store, Attribute)
    assert incompatible_members(Store, Attribute)["get"] == (
        "declared callable, implemented as a value"
    )


def test_an_uninspectable_member_is_named_rather_than_passed():
    """
    A C-implemented member carries no introspectable signature.
    Passing it silently would let an inventory count a contract as
    satisfied by something nobody compared; refusing it outright
    would be an accusation the tool cannot support. It is reported
    as unverifiable.
    """

    # `min`, not `len`: `inspect.signature(len)` succeeds and
    # returns `(obj, /)`. A first version of this test assumed
    # every builtin was opaque and was proved wrong by running it.
    # `min` genuinely raises ValueError — *no signature found for
    # builtin* — which is the case this branch exists for.
    class Builtin:
        get = min

        def __contains__(self, key: str) -> bool:
            return False

    problems = incompatible_members(Store, Builtin)

    assert problems["get"] == "call shape not introspectable"
    assert not satisfies(Store, Builtin)


def test_an_unrelated_class_satisfies_nothing():
    """
    The control case. A checker that answered `True` for
    everything would produce an inventory with no orphan
    contracts and no meaning.
    """

    class Unrelated:
        def something_else(self) -> None:
            pass

    assert not satisfies(Store, Unrelated)
    assert not satisfies(WritableStore, Unrelated)
    assert not satisfies(Check, Unrelated)


def test_satisfying_a_base_contract_does_not_satisfy_its_extension():

    class OnlyStore:
        def get(self, key: str) -> object:
            return None

        def __contains__(self, key: str) -> bool:
            return False

    assert satisfies(Store, OnlyStore)
    assert not satisfies(WritableStore, OnlyStore)
    assert missing_members(WritableStore, OnlyStore) == {"put"}
