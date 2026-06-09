"""Shared helpers for the advisor tool (beta).

The advisor tool pairs a faster executor model with a higher-intelligence
advisor model. The executor decides when to consult the advisor; Anthropic
runs the advisor as a server-side sub-inference over the executor's full
transcript and returns the advice as an advisor_tool_result block. All of
this happens inside a single /v1/messages request.

The interesting part for architects is that the feature ships with both
halves of the guide-versus-govern split:

- Prompts GUIDE: a system prompt steers when the executor calls the
  advisor, and a one-line user-message hint biases the advisor toward
  brevity. Both are soft.
- Controls GOVERN: max_tokens on the tool definition is a hard per-call
  output ceiling, max_uses is a hard per-request cap, and a client-side
  counter (see strip_advisor_blocks) is the conversation-level budget.

NOTE: the advisor tool is in beta and may be access-gated. Include the
beta header (handled below) and confirm your API key has access before
relying on these examples. See:
https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import anthropic
from dotenv import load_dotenv

load_dotenv()

BETA_HEADER = "advisor-tool-2026-03-01"
ADVISOR_TOOL_TYPE = "advisor_20260301"

DEFAULT_EXECUTOR = "claude-sonnet-4-6"
DEFAULT_ADVISOR = "claude-opus-4-8"

# Soft, prompt-level brevity request. The docs note the advisor follows
# direct address in the user message far more reliably than third-person
# instructions, and that you should ask for ~80 percent of your true
# ceiling because the limit is soft.
BREVITY_LINE = (
    "(Advisor: please keep your guidance under 80 words - I need a "
    "focused starting point, not a comprehensive plan.)"
)

# A condensed version of the timing guidance Anthropic suggests for
# coding and agent tasks. Prepend to your executor system prompt.
SUGGESTED_SYSTEM_PROMPT = """\
You have access to an `advisor` tool backed by a stronger reviewer model. \
It takes NO parameters - when you call advisor(), your entire conversation \
history is automatically forwarded.

Call advisor BEFORE substantive work - before writing, before committing \
to an interpretation, before building on an assumption. Orientation \
(reading files, fetching sources) is not substantive work. Also call \
advisor when you believe the task is complete, when stuck, or when \
considering a change of approach.

Give the advice serious weight. If you follow a step and it fails \
empirically, or primary-source evidence contradicts a specific claim, \
adapt. If your evidence and the advice conflict, surface the conflict in \
one more advisor call instead of silently switching."""

# Default demo task. Multi-step with a real planning component, so the
# advisor has something to advise on. Single-turn Q&A is a poor fit.
DEFAULT_TASK = (
    "Design and implement a small Python module that ingests camera-trap "
    "sighting records (CSV with timestamp, camera_id, species, count), "
    "deduplicates near-simultaneous sightings of the same species on the "
    "same camera within a 5 minute window, flags count anomalies, and "
    "produces a per-species summary. Plan first, then write the code."
)


def get_client() -> anthropic.Anthropic:
    """Build a client from ANTHROPIC_API_KEY in the environment or .env."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and "
            "add your key."
        )
    return anthropic.Anthropic()


def make_advisor_tool(
    model: str = DEFAULT_ADVISOR,
    max_uses: int | None = None,
    max_tokens: int | None = None,
    caching_ttl: str | None = None,
) -> dict:
    """Build the advisor tool definition.

    max_tokens is the HARD per-call ceiling on advisor output (thinking
    plus text), minimum 1024. Anthropic's testing found 2048 cut mean
    advisor output roughly 7x with near-zero truncation. max_uses caps
    advisor calls per request (not per conversation). caching_ttl of
    "5m" or "1h" turns on advisor-side prompt caching; it breaks even at
    roughly three advisor calls per conversation.
    """
    tool: dict = {"type": ADVISOR_TOOL_TYPE, "name": "advisor", "model": model}
    if max_uses is not None:
        tool["max_uses"] = max_uses
    if max_tokens is not None:
        if max_tokens < 1024:
            raise ValueError("Advisor max_tokens minimum is 1024.")
        tool["max_tokens"] = max_tokens
    if caching_ttl is not None:
        if caching_ttl not in ("5m", "1h"):
            raise ValueError('caching_ttl must be "5m" or "1h".')
        tool["caching"] = {"type": "ephemeral", "ttl": caching_ttl}
    return tool


def run_turn(
    client: anthropic.Anthropic,
    messages: list[dict],
    executor: str = DEFAULT_EXECUTOR,
    tools: list[dict] | None = None,
    system: str | None = None,
    max_tokens: int = 4096,
):
    """One Messages API call with the beta header applied.

    Note that the top-level max_tokens bounds EXECUTOR output only. It
    does not bound advisor sub-inference tokens; cap those with
    max_tokens on the tool definition instead.
    """
    kwargs: dict = dict(
        model=executor,
        max_tokens=max_tokens,
        betas=[BETA_HEADER],
        messages=messages,
    )
    if tools:
        kwargs["tools"] = tools
    if system:
        kwargs["system"] = system
    return client.beta.messages.create(**kwargs)


def with_brevity_hint(prompt: str) -> str:
    """Prefix the soft advisor-brevity line onto a user prompt."""
    return f"{BREVITY_LINE}\n\n{prompt}"


# ---------------------------------------------------------------------------
# Response inspection helpers
# ---------------------------------------------------------------------------


@dataclass
class AdvisorEvent:
    """One advisor consultation extracted from a response."""

    kind: str  # "advice", "redacted", or "error"
    text: str = ""
    stop_reason: str | None = None
    error_code: str | None = None


def extract_advisor_events(response) -> list[AdvisorEvent]:
    """Pull every advisor result out of a response, handling all three
    content variants: advisor_result, advisor_redacted_result, and
    advisor_tool_result_error."""
    events: list[AdvisorEvent] = []
    for block in response.content:
        if getattr(block, "type", None) != "advisor_tool_result":
            continue
        content = block.content
        ctype = getattr(content, "type", None)
        if ctype == "advisor_result":
            events.append(
                AdvisorEvent(
                    kind="advice",
                    text=content.text,
                    stop_reason=getattr(content, "stop_reason", None),
                )
            )
        elif ctype == "advisor_redacted_result":
            events.append(
                AdvisorEvent(
                    kind="redacted",
                    stop_reason=getattr(content, "stop_reason", None),
                )
            )
        elif ctype == "advisor_tool_result_error":
            events.append(
                AdvisorEvent(kind="error", error_code=content.error_code)
            )
    return events


def final_text(response) -> str:
    """Concatenate the executor's text blocks."""
    return "\n".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    )


@dataclass
class IterationRow:
    """One entry from usage.iterations, normalized for display."""

    kind: str  # "message" (executor) or "advisor_message"
    model: str
    input_tokens: int
    cache_read: int
    cache_creation: int
    output_tokens: int


@dataclass
class UsageSummary:
    rows: list[IterationRow] = field(default_factory=list)

    @property
    def executor_output(self) -> int:
        return sum(r.output_tokens for r in self.rows if r.kind == "message")

    @property
    def advisor_output(self) -> int:
        return sum(
            r.output_tokens for r in self.rows if r.kind == "advisor_message"
        )

    @property
    def advisor_calls(self) -> int:
        return sum(1 for r in self.rows if r.kind == "advisor_message")


def summarize_usage(response, executor: str) -> UsageSummary:
    """Normalize usage.iterations into rows. Executor and advisor
    iterations are billed at DIFFERENT model rates, which is why the
    top-level usage fields do not roll the advisor tokens in."""
    summary = UsageSummary()
    iterations = getattr(response.usage, "iterations", None) or []
    for it in iterations:
        kind = getattr(it, "type", "message")
        summary.rows.append(
            IterationRow(
                kind=kind,
                model=getattr(it, "model", executor),
                input_tokens=getattr(it, "input_tokens", 0) or 0,
                cache_read=getattr(it, "cache_read_input_tokens", 0) or 0,
                cache_creation=getattr(it, "cache_creation_input_tokens", 0)
                or 0,
                output_tokens=getattr(it, "output_tokens", 0) or 0,
            )
        )
    if not summary.rows:
        # No advisor call happened; fall back to top-level usage.
        u = response.usage
        summary.rows.append(
            IterationRow(
                kind="message",
                model=executor,
                input_tokens=u.input_tokens,
                cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
                cache_creation=getattr(u, "cache_creation_input_tokens", 0)
                or 0,
                output_tokens=u.output_tokens,
            )
        )
    return summary


def estimate_cost(
    summary: UsageSummary,
    executor_rates: tuple[float, float] | None,
    advisor_rates: tuple[float, float] | None,
) -> float | None:
    """Optional cost estimate in dollars. Rates are (input, output) in
    dollars per million tokens, supplied by the caller so this module
    never ships stale pricing. Returns None when rates are missing."""
    if executor_rates is None or advisor_rates is None:
        return None
    total = 0.0
    for row in summary.rows:
        rates = advisor_rates if row.kind == "advisor_message" else executor_rates
        total += (row.input_tokens + row.cache_read * 0.1) / 1e6 * rates[0]
        total += row.output_tokens / 1e6 * rates[1]
    return total


# ---------------------------------------------------------------------------
# Conversation-level governance
# ---------------------------------------------------------------------------


def strip_advisor_blocks(messages: list[dict]) -> list[dict]:
    """Remove advisor server_tool_use and advisor_tool_result blocks from
    a message history.

    The advisor tool has NO built-in conversation-level cap, so the
    budget is enforced client-side: count advisor calls yourself, and
    when you reach your ceiling, remove the advisor tool from the tools
    array AND strip these blocks from history. Sending history that
    still contains advisor_tool_result blocks without the tool defined
    returns a 400 invalid_request_error.

    This function is the govern half of the pattern; the system prompt
    that shapes when the executor consults the advisor is the guide half.
    """
    cleaned: list[dict] = []
    for message in messages:
        content = message.get("content")
        if message.get("role") != "assistant" or isinstance(content, str):
            cleaned.append(message)
            continue
        advisor_ids = set()
        kept = []
        for block in content:
            btype = _block_attr(block, "type")
            bname = _block_attr(block, "name")
            if btype == "server_tool_use" and bname == "advisor":
                advisor_ids.add(_block_attr(block, "id"))
                continue
            if btype == "advisor_tool_result" and (
                _block_attr(block, "tool_use_id") in advisor_ids
                or not advisor_ids
            ):
                continue
            kept.append(block)
        cleaned.append({"role": "assistant", "content": kept})
    return cleaned


def count_advisor_calls(messages: list[dict]) -> int:
    """Count advisor consultations across a conversation history."""
    count = 0
    for message in messages:
        content = message.get("content")
        if message.get("role") != "assistant" or isinstance(content, str):
            continue
        for block in content:
            if (
                _block_attr(block, "type") == "server_tool_use"
                and _block_attr(block, "name") == "advisor"
            ):
                count += 1
    return count


def _block_attr(block, name: str):
    if isinstance(block, dict):
        return block.get(name)
    return getattr(block, name, None)
