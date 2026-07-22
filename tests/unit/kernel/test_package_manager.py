from aistack.kernel.engines import PackageManager


def test_package_manager_exists() -> None:
    manager = PackageManager()

    assert isinstance(manager, PackageManager)
