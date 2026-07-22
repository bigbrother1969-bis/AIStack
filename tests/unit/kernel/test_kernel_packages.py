import importlib


def test_kernel_packages_exist() -> None:
    assert importlib.import_module("aistack.kernel.engines")
    assert importlib.import_module("aistack.kernel.repositories")
    assert importlib.import_module("aistack.kernel.capabilities")
