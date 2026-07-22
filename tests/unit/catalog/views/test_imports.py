from aistack.catalog.views import (
    CatalogView,
    CatalogViewEngine,
    CatalogViewItem,
)


def test_catalog_views_public_api():
    assert CatalogView is not None
    assert CatalogViewItem is not None
    assert CatalogViewEngine is not None
