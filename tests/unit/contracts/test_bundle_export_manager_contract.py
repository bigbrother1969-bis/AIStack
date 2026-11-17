from aistack.contracts.bundle_export_manager import (
    BundleExportManager,
)


def test_bundle_export_manager_is_abstract():

    try:
        BundleExportManager()

        assert False

    except TypeError:
        assert True
