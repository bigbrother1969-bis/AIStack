from __future__ import annotations

from aistack.ai_runtime.operations import _LANGUAGE_DIRECTIVE


def test_the_french_directive_asks_for_tutoiement_as_its_last_word():
    directive = _LANGUAGE_DIRECTIVE["fr"]

    assert "Tutoie le lecteur" in directive and "jamais « vous »" in directive
    assert "\n" not in directive.strip()  # one closing instruction, at the end of the prompt
