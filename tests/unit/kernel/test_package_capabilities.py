from aistack.kernel.capabilities.package import (
    CompressCapability,
    DecompressCapability,
    DecryptCapability,
    DeserializeCapability,
    EncryptCapability,
    SerializeCapability,
    SignCapability,
    VerifySignatureCapability,
    HashCapability,
)
from aistack.kernel.contracts import PackageCapability


def test_package_capabilities_implement_contract():
    for capability in (
        CompressCapability,
        DecompressCapability,
        DecryptCapability,
        DeserializeCapability,
        EncryptCapability,
        SerializeCapability,
        SignCapability,
        VerifySignatureCapability,
        HashCapability,
    ):
        assert issubclass(capability, PackageCapability)
