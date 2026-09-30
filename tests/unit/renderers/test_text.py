from aistack.renderers.text import domain_slug, escape_text


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


def test_domain_slug_lowercases_and_hyphenates():
    assert domain_slug("Tests PRA") == "tests-pra"
    assert domain_slug("Stockage") == "stockage"


def test_domain_slug_collapses_punctuation_and_strips_leading_trailing_hyphens():
    assert domain_slug("Sauvegarde / PRA") == "sauvegarde-pra"
    assert domain_slug("Écarts d'inventaire") == "carts-d-inventaire"


def test_domain_slug_falls_back_to_a_placeholder_for_an_all_punctuation_name():
    assert domain_slug("???") == "domain"


def test_domain_slug_is_unique_across_every_real_health_cockpit_domain_name():
    """
    `aistack.cli.health_render.build_cockpit`'s own seven domain
    names, slugged — the exact set `aistack.renderers.health.html`
    anchors and `aistack.renderers.console.html` links to. A
    collision here would mean two different domains' sections land
    on the same `console.html` -> `health.html#domain-<slug>` anchor,
    not merely an ugly id.
    """

    names = (
        "Stockage",
        "Services",
        "Sauvegarde / PRA",
        "GPU",
        "Tests PRA",
        "État persistant",
        "Écarts d'inventaire",
    )
    slugs = [domain_slug(name) for name in names]

    assert len(set(slugs)) == len(slugs)
