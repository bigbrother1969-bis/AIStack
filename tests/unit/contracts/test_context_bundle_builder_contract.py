from aistack.contracts.context_bundle_builder import (
    ContextBundleBuilder,
)


def test_context_bundle_builder_is_abstract():

    try:
        ContextBundleBuilder()

        assert False, "ContextBundleBuilder must be abstract"

    except TypeError:
        assert True
