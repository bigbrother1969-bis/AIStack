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
# principle — "AI is a reasoning assistant, never a source of truth" —
# means the deterministic Runtime's own qualification
# (`aistack.runtime.evaluate`, `OPS-0004`) is the one thing here that
# is not up for the model's own opinion; what the model adds is
# reasoning *about* it, in language, not a second verdict on whether
# it is true.
#
# **Every prompt asks for a French answer** — owner's explicit choice
# (2026-09-18, `claude/PLAN-TROUBLESHOOTING-ASSISTANT-UI-2026-09-18
# .md`), made for the whole patrimoine rather than only the new
# guided UI: the CLI (`aistack.cli.ai_reason`) and J7's stored
# history (`aistack.ai_runtime.reasoning_history`) inherit it too,
# since both call these same three functions. Deliberately not
# extended to the finding's own `interpretation`/`remediation` text —
# that is the governed `OPS-0004` rule's own declared wording
# (`aistack.runtime.evaluate`), not something this module produces,
# and the owner chose to leave it as the rule states it (English),
# everywhere it already appears (CLI, Cockpit Santé). The directive
# lives at the end of each template, after the finding's own fields —
# asking last, once the model has already read what it is reasoning
# about, is the same ordering QUAL-0001 found more reliable for
# small models than a leading instruction.

_MODEL_NOT_CONFIGURED = (
    "no model is configured (aistack.ai_runtime.definitions."
    "ai_runtime.yml has no model:); run `ollama list` on the host "
    "this points at and set it before asking the AI Runtime anything"
)


def reason(
    finding: RuntimeFinding, engine: AIEngine, model: str | None
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
    """

    return _ask("reason", finding, engine, model, _REASON_PROMPT)


def explain(
    finding: RuntimeFinding, engine: AIEngine, model: str | None
) -> AIRuntimeAnswer:
    """
    Ask the AI Runtime to explain one `RuntimeFinding` in plain
    language, for the owner rather than for another rule.
    """

    return _ask("explain", finding, engine, model, _EXPLAIN_PROMPT)


def recommend(
    finding: RuntimeFinding, engine: AIEngine, model: str | None
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
    """

    return _ask("recommend", finding, engine, model, _RECOMMEND_PROMPT)


def _ask(
    operation: str,
    finding: RuntimeFinding,
    engine: AIEngine,
    model: str | None,
    prompt_template: str,
) -> AIRuntimeAnswer:
    if not model:
        return AIRuntimeAnswer(
            operation=operation,
            subject=finding.subject,
            model="",
            prompt="",
            response="",
            reachable=False,
            unreachable_reason=_MODEL_NOT_CONFIGURED,
        )

    prompt = prompt_template.format(**_describe(finding))
    text, reason_ = engine.complete(prompt)

    return AIRuntimeAnswer(
        operation=operation,
        subject=finding.subject,
        model=model,
        prompt=prompt,
        response=text,
        reachable=bool(text),
        unreachable_reason=reason_,
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

In two or three sentences, reason about what this finding means for \
the system it describes. Do not repeat the interpretation verbatim; \
add context a reader would not already have from it alone.

Réponds uniquement en français, même si tout ce qui précède est en \
anglais.
"""

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

In plain, non-technical language, explain what this finding is \
telling the owner and why it was flagged. Keep it short.

Réponds uniquement en français, même si tout ce qui précède est en \
anglais.
"""

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

Suggest one concrete next step the owner could take, building on \
the declared remediation above rather than replacing it. State \
clearly that this is a suggestion for the owner to judge, not an \
instruction.

Réponds uniquement en français, même si tout ce qui précède est en \
anglais.
"""
