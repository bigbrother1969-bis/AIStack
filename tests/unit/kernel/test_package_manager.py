from aistack.kernel.engines import PackageManager
from aistack.kernel.models import KnowledgePackage


def test_package_manager_exists() -> None:
    manager = PackageManager()

    assert isinstance(manager, PackageManager)


def test_package_manager_returns_same_package() -> None:
    manager = PackageManager()

    package = KnowledgePackage(
        id="knowledge-package-001",
    )

    assert manager.package(package) is package
    assert manager.unpackage(package) is package
