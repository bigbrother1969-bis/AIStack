from __future__ import annotations

from aistack.ai_runtime.engine import AIEngine
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding

# Three operations, each a separate prompt over the same finding. Every
# prompt states the finding as established fact: the model reasons about the
# deterministic qualification (`aistack.runtime`, `OPS-0004`), it never
# judges whether it is true.
#
# The answer must come back in `target_language`. Small models often ignore
# a language instruction, so for a non-English target an optional second,
# fast `translator` engine translates the answer. The finding's own
# `interpretation`/`remediation` text is not translated. The language
# directive sits at the end of each template, which small models follow
# more reliably than a leading instruction.

_MODEL_NOT_CONFIGURED = (
    "no model is configured (aistack.ai_runtime.definitions."
    "ai_runtime.yml has no model:); run `ollama list` on the host "
    "this points at and set it before asking the AI Runtime anything"
)

# One entry per declared UI language. An undeclared language is refused,
# never guessed; adding a language means adding it here and to
# `_LANGUAGE_NAME`.
_LANGUAGE_DIRECTIVE: dict[str, str] = {
    "fr": (
        "\nRéponds uniquement en français, même si tout ce qui "
        "précède est en anglais.\n"
    ),
    # No directive: models already answer in English, and the translation
    # pass is skipped for English too.
    "en": "",
}

# Language names for the translation prompt (non-English targets only).
_LANGUAGE_NAME: dict[str, str] = {
    "fr": "French",
    "en": "English",
}


def reason(
    finding: RuntimeFinding,
    engine: AIEngine,
    model: str | None,
    *,
    target_language: str = "fr",
    translator: AIEngine | None = None,
    context: str = "",
) -> AIRuntimeAnswer:
    """
    Ask the engine to reason about one `RuntimeFinding`: what it means,
    read alongside what it cites.

    With `model` `None` (not configured), nothing is sent and the answer is
    marked unreachable. `target_language` is the language the answer must
    come back in; `translator`, if given, translates a non-English answer.
    `context` adds the facts collected on the host to the prompt.
    """

    return _ask(
        "reason", finding, engine, model, _REASON_PROMPT,
        target_language, translator, context,
    )


def explain(
    finding: RuntimeFinding,
    engine: AIEngine,
    model: str | None,
    *,
    target_language: str = "fr",
    translator: AIEngine | None = None,
    context: str = "",
) -> AIRuntimeAnswer:
    """
    Ask the engine to explain one `RuntimeFinding` in plain language for the
    user. Parameters as in `reason`.
    """

    return _ask(
        "explain", finding, engine, model, _EXPLAIN_PROMPT,
        target_language, translator, context,
    )


def recommend(
    finding: RuntimeFinding,
    engine: AIEngine,
    model: str | None,
    *,
    target_language: str = "fr",
    translator: AIEngine | None = None,
    context: str = "",
) -> AIRuntimeAnswer:
    """
    Ask the engine to suggest a next step for one `RuntimeFinding`. The
    prompt states that the answer is a suggestion, never an instruction to
    carry out. Parameters as in `reason`.
    """

    return _ask(
        "recommend", finding, engine, model, _RECOMMEND_PROMPT,
        target_language, translator, context,
    )


def _ask(
    operation: str,
    finding: RuntimeFinding,
    engine: AIEngine,
    model: str | None,
    prompt_template: str,
    target_language: str,
    translator: AIEngine | None,
    context: str = "",
) -> AIRuntimeAnswer:
    if target_language not in _LANGUAGE_DIRECTIVE:
        raise ValueError(
            f"{operation}: no language directive declared for "
            f"{target_language!r}; add one to _LANGUAGE_DIRECTIVE "
            f"(aistack.ai_runtime.operations) before asking for it"
        )

    if not model:
        return AIRuntimeAnswer(
            operation=operation,
            subject=finding.subject,
            model="",
            prompt="",
            response="",
            reachable=False,
            unreachable_reason=_MODEL_NOT_CONFIGURED,
            language=target_language,
        )

    prompt = prompt_template.format(
        **_describe(finding),
        context_block=_CONTEXT_BLOCK.format(context=context.strip()) if context.strip() else "",
        language_directive=_LANGUAGE_DIRECTIVE[target_language],
    )
    text, reason_ = engine.complete(prompt)

    # Enforce the target language with the translator, except for English
    # or when no translator is configured. Best-effort: if translation fails,
    # the original answer is kept, and its language is not re-checked.
    if text and translator is not None and target_language != "en":
        translated, _reason = translator.complete(
            _TRANSLATE_PROMPT.format(
                language=_LANGUAGE_NAME[target_language], text=text
            )
        )

        if translated:
            text = translated

    return AIRuntimeAnswer(
        operation=operation,
        subject=finding.subject,
        model=model,
        prompt=prompt,
        response=text,
        reachable=bool(text),
        unreachable_reason=reason_,
        language=target_language,
    )


def _describe(finding: RuntimeFinding) -> dict[str, str]:
    qualifications = (
        ", ".join(finding.qualifications)
        if finding.qualifications
        else "none"
    )

    return {
        "subject": finding.subject,
        "signature": finding.signature,
        "interpretation": finding.interpretation,
        "remediation": finding.remediation,
        "confidence": finding.confidence,
        "qualifications": qualifications,
    }


# Facts AIStack measured or declared on the host, sent with the question so
# the answer is about this host. Empty context leaves the prompt unchanged.
_CONTEXT_BLOCK = """
What AIStack measured or declared on the host about this finding — \
also established fact, to build on, never to contradict:
{context}
"""

_TRANSLATE_PROMPT = """\
Translate the following text into {language}. Reply with only the \
translation itself — no preface, no explanation, no quotation marks, \
and no note about the translation.

{text}
"""

_REASON_PROMPT = """\
You are the AI Runtime of AIStack, a homelab knowledge operating \
system. You never invent facts and you never contradict what the \
deterministic Runtime already established below — you reason about \
it in plain language.

A governed rule produced this finding, already qualified. Treat \
every line below as established fact, not as something to verify:

subject: {subject}
signature: {signature}
qualifications: {qualifications}
confidence: {confidence}
interpretation: {interpretation}
declared remediation: {remediation}
{context_block}
In two or three sentences, reason about what this finding means for \
the system it describes. Do not repeat the interpretation verbatim; \
add context a reader would not already have from it alone.
{language_directive}"""

_EXPLAIN_PROMPT = """\
You are the AI Runtime of AIStack, a homelab knowledge operating \
system. You never invent facts and you never contradict what the \
deterministic Runtime already established below — you explain it in \
plain language, for the person who owns this homelab, not for \
another automated rule.

A governed rule produced this finding, already qualified. Treat \
every line below as established fact, not as something to verify:

subject: {subject}
signature: {signature}
qualifications: {qualifications}
confidence: {confidence}
interpretation: {interpretation}
declared remediation: {remediation}
{context_block}
In plain, non-technical language, explain what this finding is \
telling the owner and why it was flagged. Keep it short.
{language_directive}"""

_RECOMMEND_PROMPT = """\
You are the AI Runtime of AIStack, a homelab knowledge operating \
system. You never invent facts and you never contradict what the \
deterministic Runtime already established below. You are a \
reasoning assistant, never a source of truth and never an executor \
— what you produce is a suggestion for the owner to evaluate, never \
an instruction that gets carried out on its own.

A governed rule produced this finding, already qualified. Treat \
every line below as established fact, not as something to verify:

subject: {subject}
signature: {signature}
qualifications: {qualifications}
confidence: {confidence}
interpretation: {interpretation}
declared remediation: {remediation}
{context_block}
Suggest one concrete next step the owner could take, building on \
the declared remediation above rather than replacing it. State \
clearly that this is a suggestion for the owner to judge, not an \
instruction.
{language_directive}"""
