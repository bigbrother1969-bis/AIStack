from aistack.runtime.deployment_definition import extract_dockerfile_command


def test_a_json_array_cmd_is_joined_with_spaces():

    document = (
        "FROM python:3.13-slim\n"
        "WORKDIR /app\n"
        'CMD ["python3","-m","uvicorn","app:app","--host","0.0.0.0"]\n'
    )

    assert (
        extract_dockerfile_command(document)
        == "python3 -m uvicorn app:app --host 0.0.0.0"
    )


def test_a_shell_form_cmd_is_returned_verbatim():

    document = "FROM python:3.13-slim\nCMD python3 -m uvicorn app:app\n"

    assert extract_dockerfile_command(document) == "python3 -m uvicorn app:app"


def test_a_dockerfile_with_no_cmd_returns_none():

    document = "FROM python:3.13-slim\nWORKDIR /app\n"

    assert extract_dockerfile_command(document) is None


def test_the_last_cmd_wins():
    """
    Only one `CMD` is ever in effect at build time, even if a
    Dockerfile declares several — Docker's own semantics.
    """

    document = (
        'CMD ["python3", "one.py"]\n'
        "RUN echo unrelated\n"
        'CMD ["python3", "two.py"]\n'
    )

    assert extract_dockerfile_command(document) == "python3 two.py"


def test_indentation_and_surrounding_whitespace_are_tolerated():

    document = '  CMD ["python3", "app.py"]  \n'

    assert extract_dockerfile_command(document) == "python3 app.py"


def test_a_malformed_json_array_falls_back_to_the_raw_text():

    document = "CMD [python3, app.py]\n"

    assert extract_dockerfile_command(document) == "[python3, app.py]"


def test_an_empty_document_returns_none():

    assert extract_dockerfile_command("") is None


def test_a_cmd_naming_a_non_list_json_value_returns_the_raw_text():
    """
    `CMD "python3 app.py"` is valid JSON — a bare string — but not
    the array form this function rejoins; the raw text is what
    Docker itself would treat as the command in that case too.
    """

    document = 'CMD "python3 app.py"\n'

    assert extract_dockerfile_command(document) == '"python3 app.py"'
