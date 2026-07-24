from aistack.contracts.context_bundle_service import (
    ContextBundleService,
)


def test_context_bundle_service_is_abstract():

    try:
        ContextBundleService()

        assert False, (
            "ContextBundleService must be abstract"
        )

    except TypeError:
        assert True
