from __future__ import annotations

from aistack.ai_runtime.engine import AIEngine
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding

# `ARCH-0003-AI-Runtime-Architecture.md` § Operations names six;
# `claude/PLAN-TRAJECTOIRE-2026-09-04.md` J6 asks for three of them —
# `summarize`/`validate_with_context`/`generate_draft_artifact` are
# named there but not built here, per the owner's own scoping
# decision 2026-09-13. Each function below is a separate prompt over
# the same finding, not three code paths through one prompt, so a
# fourth operation is a fourth function added beside these, not a
# branch inside one.
#
# **Every prompt states the finding as already-established fact,
# never asks the model to judge whether it is correct.** `ARCH-0003`'s
# own principle — "AI is a reasoning assistant, never a source of
# truth" — means the deterministic Runtime's own qualification
# (`aistack.runtime.evaluate`, `OPS-0004`) is the one thing here that
# is not up for the model's own opinion; what the model adds is
# reasoning *about* it, in language, not a second verdict on whether
# it is true.
#
# **The answer must come back in `target_language`, not always in
# French — corrected 2026-09-27.** The original design (2026-09-18,
# `claude/PLAN-TROUBLESHOOTING-ASSISTANT-UI-2026-09-18.md`) asked
# every prompt for French unconditionally, for the whole patrimoine
# (CLI and the guided UI alike). The owner's own real use of the
# guided UI found the opposite of what that design assumed:
# `deepseek-r1:1.5b` does not reliably follow a French-only
# instruction — the answers came back in English regardless — which
# also made the README/RELEASE-NOTES 1.2.0 claim ("the AI Runtime's
# own answers stay in French") false the day it was published. The
# owner's fix, chosen over a stricter prompt or a different model
# (2026-09-27): keep asking the model in its prompt, but *enforce* the
# target language with a second, fast translation pass
# (`qwen2.5:0.5b` — already confirmed installed, `ai_runtime.yml`'s
# own `ollama list` note, 2026-09-18) whenever the target is not
# English — and skip that pass for English, since the model's own
# unprompted behaviour already satisfies it. `target_language` is the
# *display* language the caller is answering for: the CLI keeps the
# original French-for-the-whole-patrimoine default (it has no
# "display" of its own to follow), and the guided UI now passes
# whatever language the visitor is reading the page in
# (`aistack.web.troubleshooting`'s own `_language(request)`),
# not a language hardcoded here.
#
# Deliberately not extended to the finding's own `interpretation`/
# `remediation` text — that is the governed `OPS-0004` rule's own
# declared wording (`aistack.runtime.evaluate`), not something this
# module produces, and the owner chose to leave it as the rule states
# it (English), everywhere it already appears (CLI, Cockpit Santé).
# The directive lives at the end of each template, after the
# finding's own fields — asking last, once the model has already read
# what it is reasoning about, is the same ordering QUAL-0001 found
# more reliable for small models than a leading instruction.

_MODEL_NOT_CONFIGURED = (
    "no model is configured (aistack.ai_runtime.definitions."
    "ai_runtime.yml has no model:); run `ollama list` on the host "
    "this points at and set it before asking the AI Runtime anything"
)

# One entry per language `aistack.i18n.definitions.languages.yml`
# declares today (fr, en) — asking for a language this dict does not
# name is refused rather than silently asking for nothing, the same
# "undeclared is refused, never guessed" convention
# `aistack.i18n.catalog._flag_uri` already holds for a language's own
# flag. Adding a third declared language means adding its own line
# here and to `_LANGUAGE_NAME` below, not a fallback that pretends
# every unlisted code is fine.
_LANGUAGE_DIRECTIVE: dict[str, str] = {
    "fr": (
        "\nRéponds uniquement en français, même si tout ce qui "
        "précède est en anglais.\n"
    ),
    # No directive at all — the model's own unprompted behaviour is
    # already English often enough that the owner's own real use
    # found no French-only instruction reliably changes it either;
    # asking for what it already tends to do adds nothing, and the
    # translation pass below is skipped for English for the same
    # reason (2026-09-27).
    "en": "",
}

# Only used for a non-English target — see `_ask`'s own translation
# step. "fr" is the only one in real use today (English never reaches
# `_translate`), kept alongside it so a third declared language adds
# one line here too, not a guess at how to name itself in English.
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
    Ask the AI Runtime to reason about one `RuntimeFinding` — what it
    means, read alongside what it cites.

    **`model` may be `None`, and that is answered here rather than
    left to the caller** — `aistack.ai_runtime.definition
    .AIRuntimeDefinition.model` is `None` until the owner fills it
    in, and every one of `reason`/`explain`/`recommend` would
    otherwise repeat the same guard. `engine` is still asked for
    nothing in that case — no request is sent naming a model nobody
    confirmed is installed.

    **`target_language`/`translator`** — see this module's own
    docstring, 2026-09-27: `target_language` names the language the
    answer must come back in (default `"fr"`, the CLI's own
    unchanged choice); `translator` is a second `AIEngine` — a fast
    model's own connection, never `engine` again — asked to translate
    into `target_language` when it is not `"en"`. Left `None`, no
    translation is attempted and the raw answer is returned exactly
    as `engine` gave it, the same as before this parameter existed.
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
    Ask the AI Runtime to explain one `RuntimeFinding` in plain
    language, for the owner rather than for another rule.

    `target_language`/`translator` — see `reason`'s own docstring.
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
    Ask the AI Runtime to suggest a next step for one `RuntimeFinding`.

    **A suggestion, stated as one in the prompt itself, never an
    instruction the AI Runtime could be mistaken for having
    authority to carry out.** `claude/PLAN-TRAJECTOIRE-2026-09-04.md`
    J8 — the assistant this operation eventually feeds — states the
    same rule for its own recommendation: "jamais exécutée seule."
    Nothing about that changes because J8 is not built yet; the
    prompt says so from this operation's first real call.

    `target_language`/`translator` — see `reason`'s own docstring.
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

    # Enforce `target_language` rather than trust the instruction
    # already inside `prompt` — 2026-09-27, this module's own
    # docstring. Skipped for English (nothing to enforce that the
    # model does not already do on its own) and whenever no
    # `translator` was given (the caller declared none configured;
    # the raw answer travels unchanged, exactly as before this
    # feature existed — never blocked on a second model nobody
    # confirmed is installed, the same reasoning `model` itself
    # already gets).
    #
    # **Best-effort, not verified.** A translation call that fails
    # (`translator.complete` returns no text) leaves `text` exactly
    # as `engine` gave it — still a real, reachable answer, just not
    # provably in `target_language`; nothing here re-checks the
    # language of what came back, from either engine.
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


# The facts AIStack measured or declared on the host (the assistant's
# step 2), sent with the question so the answer is about this host
# (the owner, 2026-10-09: "on envoie les faits pour mieux cibler la
# réponse"). Empty: the prompts are exactly as before.
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
