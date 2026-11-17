from aistack.contracts.bundle_exporter import BundleExporter


def test_bundle_exporter_is_abstract():

    try:
        BundleExporter()

        assert False, "BundleExporter must be abstract"

    except TypeError:
        assert True
