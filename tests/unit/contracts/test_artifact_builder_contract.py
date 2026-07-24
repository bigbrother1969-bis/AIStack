from aistack.contracts.artifact_builder import ArtifactBuilder


def test_artifact_builder_is_abstract():

    try:
        ArtifactBuilder()

        assert False, "ArtifactBuilder must be abstract"

    except TypeError:
        assert True
