from aistack.contracts.registry_builder import RegistryBuilder


def test_registry_builder_is_abstract():

    try:
        RegistryBuilder()

        assert False, "RegistryBuilder must be abstract"

    except TypeError:
        assert True
