from aistack.renderers.text import escape_text


def test_escape_text_handles_all_four_characters_independently():
    assert escape_text('a & b " c < d > e') == "a &amp; b &quot; c &lt; d &gt; e"
    assert escape_text("plain") == "plain"


def test_escape_text_is_still_reachable_from_the_architecture_mermaid_module():
    """
    `aistack.renderers.architecture.mermaid` re-exports `escape_text`
    from here rather than defining it — this is the compatibility
    that move relies on, checked directly rather than only implied by
    `test_mermaid.py` still passing.
    """

    from aistack.renderers.architecture.mermaid import escape_text as reexported

    assert reexported is escape_text
