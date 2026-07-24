from aistack.contracts.manifest_serializer import (
    ManifestSerializer,
)


class DummyManifestSerializer(
    ManifestSerializer
):

    def serialize(self, manifest):
        return "{}"


def test_manifest_serializer_contract():

    serializer = DummyManifestSerializer()

    assert serializer.serialize(None) == "{}"
