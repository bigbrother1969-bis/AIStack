from aistack.contracts.context_bundle_engine import (
    ContextBundleEngine,
)


def test_context_bundle_engine_is_abstract():

    try:
        ContextBundleEngine()

        assert False, (
            "ContextBundleEngine must be abstract"
        )

    except TypeError:
        assert True
