from aistack.providers.nextcloud import verify_uploads


def _download_matching(size: int, sha256: str = "deadbeef"):
    def download(_name: str) -> dict:
        return {
            "downloaded": True,
            "reason": "",
            "downloaded_size": size,
            "sha256": sha256,
        }

    return download


def test_a_file_whose_size_agrees_on_both_requests_is_verified():
    files = [{"name": "IMG_0001.HEIC", "size": 2048576}]

    result = verify_uploads(files, _download_matching(2048576))

    assert result == [
        {
            "name": "IMG_0001.HEIC",
            "verified": True,
            "reason": "",
            "size": 2048576,
            "sha256": "deadbeef",
        }
    ]


def test_a_size_mismatch_is_not_verified_and_says_both_numbers():
    files = [{"name": "IMG_0001.HEIC", "size": 2048576}]

    result = verify_uploads(files, _download_matching(2048000))

    assert result[0]["verified"] is False
    assert "2048576" in result[0]["reason"]
    assert "2048000" in result[0]["reason"]


def test_a_file_propfind_reported_no_size_for_is_not_verified():
    """
    Nothing to recoup the download against — reported honestly as
    unverifiable rather than assumed safe.
    """

    files = [{"name": "IMG_0001.HEIC", "size": None}]

    result = verify_uploads(files, _download_matching(2048576))

    assert result[0]["verified"] is False
    assert "did not report a size" in result[0]["reason"]


def test_a_failed_download_is_reported_not_dropped():
    files = [{"name": "IMG_0001.HEIC", "size": 2048576}]

    def download(_name: str) -> dict:
        return {
            "downloaded": False,
            "reason": "Nextcloud refused GET ... with status 401",
            "downloaded_size": None,
            "sha256": None,
        }

    result = verify_uploads(files, download)

    assert result == [
        {
            "name": "IMG_0001.HEIC",
            "verified": False,
            "reason": "Nextcloud refused GET ... with status 401",
            "size": 2048576,
            "sha256": None,
        }
    ]


def test_every_file_gets_its_own_entry_even_when_some_fail():
    files = [
        {"name": "IMG_0001.HEIC", "size": 100},
        {"name": "IMG_0002.HEIC", "size": 200},
    ]

    def download(name: str) -> dict:
        if name == "IMG_0001.HEIC":
            return {
                "downloaded": True,
                "reason": "",
                "downloaded_size": 100,
                "sha256": "aaa",
            }
        return {
            "downloaded": False,
            "reason": "did not answer within 5.0 seconds",
            "downloaded_size": None,
            "sha256": None,
        }

    result = verify_uploads(files, download)

    assert [entry["name"] for entry in result] == [
        "IMG_0001.HEIC",
        "IMG_0002.HEIC",
    ]
    assert result[0]["verified"] is True
    assert result[1]["verified"] is False


def test_download_is_called_once_per_file_by_name():
    files = [
        {"name": "IMG_0001.HEIC", "size": 100},
        {"name": "IMG_0002.HEIC", "size": 200},
    ]
    seen = []

    def download(name: str) -> dict:
        seen.append(name)
        return {
            "downloaded": True,
            "reason": "",
            "downloaded_size": files[len(seen) - 1]["size"],
            "sha256": "x",
        }

    verify_uploads(files, download)

    assert seen == ["IMG_0001.HEIC", "IMG_0002.HEIC"]
