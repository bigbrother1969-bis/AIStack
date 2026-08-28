from pathlib import Path

from aistack.context_bundle.transfer.ssh_bundle_transfer import (
    SshBundleTransfer,
)


def test_ssh_bundle_transfer_contract():

    transfer = SshBundleTransfer()

    assert isinstance(
        transfer,
        object,
    )


# --------------------------------------------------------------------
# The contract it declares is the one it honours
# --------------------------------------------------------------------


def test_it_declares_the_contract_it_actually_satisfies():
    """
    It declared `BundleTransfer` until 2026-08-27 and did not
    implement it: that contract is the transport —
    `transfer(source, target)`, destination supplied by the
    caller — and this class takes one argument and builds its own
    destination from configuration.

    **Python's ABC machinery never looks at signatures.** It
    checks that a method of the right name exists, so
    instantiating the mismatched class was allowed and
    `DefaultContextBundleService` went on annotating its
    parameter `ContextBundleTransferService | None` while
    production handed it a `BundleTransfer`.

    **The heritage's own instrument was not fooled**, and that is
    the interesting half: `aistack.conformance.structural.satisfies`
    compares call shapes, so it never counted this class among
    `BundleTransfer`'s implementations. What no instrument reports
    is the declaration itself — a class naming a base whose
    contract it does not satisfy. GOV-0002/OS-040.

    **This test asserted only the first two lines until
    2026-08-28, and that is why the correction was incomplete.**
    `issubclass` is the declaration — the half that was never in
    doubt after the base was changed — and the class went on
    declaring `transfer(bundle_path)` while implementing
    `transfer(source)`. `false-declarations` found it on the day
    it was written. The third assertion is the one that was
    missing: a declaration is checked against the call shape, not
    against the class hierarchy.
    """

    from aistack.conformance.structural import satisfies
    from aistack.contracts.bundle_transfer import BundleTransfer
    from aistack.contracts.context_bundle_transfer_service import (
        ContextBundleTransferService,
    )

    assert issubclass(SshBundleTransfer, ContextBundleTransferService)

    assert not issubclass(SshBundleTransfer, BundleTransfer)

    assert satisfies(ContextBundleTransferService, SshBundleTransfer)


def test_the_transport_contract_keeps_an_implementation_that_honours_it():
    """
    The other direction, and it is why this correction is not a
    deletion. `BundleTransfer` is not left orphaned:
    `FileSystemBundleTransfer` implements it with the two
    arguments it declares, and `DefaultContextBundleTransferService`
    consumes it that way.
    """

    import inspect

    from aistack.contracts.bundle_transfer import BundleTransfer
    from aistack.context_bundle.transfer.bundle_transfer import (
        FileSystemBundleTransfer,
    )

    assert issubclass(FileSystemBundleTransfer, BundleTransfer)

    declared = inspect.signature(BundleTransfer.transfer).parameters
    implemented = inspect.signature(
        FileSystemBundleTransfer.transfer
    ).parameters

    assert list(declared) == list(implemented)
