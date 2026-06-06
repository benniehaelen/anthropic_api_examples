"""
Shared building blocks for the prompt-caching example.

Prompt caching lets you reuse a large, stable prompt prefix across many requests: you pay a
small write premium once, then later requests read the prefix back at ~0.1x input price (and
faster). It is a **prefix match** — any byte change before a `cache_control` breakpoint
invalidates the cache from that point on. Render order is `tools` → `system` → `messages`, so a
single breakpoint on the last system block caches the tools **and** the system prompt together.

This module builds a large cacheable prefix (a synthetic employee handbook + system instructions
+ a tool), runs questions with caching on or off, and reports the usage metrics that prove it
worked. Imported by `caching_demo.ipynb`, `cache_app.py`, and `run_cache.py`.

Measure with `usage`: `cache_creation_input_tokens` (written this request, ~1.25x),
`cache_read_input_tokens` (served from cache, ~0.1x), `input_tokens` (full-price remainder).
"""

import time

# Sonnet 4.5 to keep repeated calls cheap. Note the minimum cacheable prefix is model-dependent:
# 1024 tokens on Sonnet 4.5 but 4096 on Opus 4.8 — the handbook below clears 4096 so it caches
# on either. Caches are model-scoped; switching models is a full cache miss.
MODEL = "claude-sonnet-4-5"


# --------------------------------------------------------------------------- #
# The cacheable content (generated test data)
# --------------------------------------------------------------------------- #
# Hand-written policy sections carry the facts the demo questions ask about.
_POLICIES = [
    ("Paid time off",
     "New employees receive 18 paid vacation days per year, accruing at 1.5 days per month. "
     "Unused days roll over up to a maximum of 10 days into the following year. Vacation must be "
     "requested at least two weeks in advance through the People portal."),
    ("Remote work",
     "Employees may work remotely up to three days per week. Fully remote arrangements require "
     "director approval and a signed remote-work agreement. Core collaboration hours are "
     "10:00–15:00 local time, during which everyone is expected to be reachable."),
    ("Expense reimbursement",
     "Submit expense reports through the Finance portal within 30 days of the expense. Receipts "
     "are required for any item above $25. Meals while travelling are reimbursed up to $60 per "
     "day. Reimbursements are paid out on the next payroll cycle after approval."),
    ("Information security",
     "Passwords must be at least 14 characters and rotated every 90 days. Multi-factor "
     "authentication is mandatory for all internal systems. Never share credentials; report any "
     "suspected phishing to security@acme.example within one hour."),
    ("Equipment",
     "Each employee receives a laptop refreshed every three years. Monitors, keyboards, and "
     "headsets are available on request through IT. Lost or stolen equipment must be reported to "
     "IT immediately so the device can be remotely wiped."),
    ("Parental leave",
     "Birthing parents receive 16 weeks of fully paid leave; non-birthing parents receive 8 "
     "weeks. Leave may be taken any time within the first year and can be split into at most two "
     "blocks. Notify People at least 30 days before the intended start date."),
    ("Learning budget",
     "Every employee has an annual learning budget of $1,500 for courses, books, and "
     "conferences. Certification exam fees are fully covered and do not count against the budget. "
     "Unused learning budget does not roll over."),
    ("Code of conduct",
     "Treat colleagues with respect, assume good intent, and disclose conflicts of interest. "
     "Harassment of any kind results in disciplinary action up to termination. Concerns can be "
     "raised anonymously through the ethics hotline."),
    ("Travel",
     "Book flights at least 14 days ahead through the corporate travel tool. Economy is standard; "
     "business class is permitted for flights over 6 hours with manager approval. Personal travel "
     "may be combined with business trips at the employee's own cost."),
    ("Performance reviews",
     "Formal reviews happen twice a year, in June and December. Ratings range from 1 (below "
     "expectations) to 5 (exceptional). Promotions are considered during the December cycle and "
     "require a rating of 4 or higher in the prior two reviews."),
    ("Health benefits",
     "Medical, dental, and vision coverage begin on the first day of employment. The company "
     "covers 100% of the employee premium and 75% of dependent premiums. Open enrollment runs "
     "each November."),
    ("Holidays",
     "The company observes 11 public holidays plus a company-wide winter shutdown from December "
     "24 to January 1. Employees also receive two floating holidays to use for occasions of "
     "personal significance."),
]


def build_handbook():
    """Assemble a deterministic, sizable handbook (> 4096 tokens so it caches on any model)."""
    parts = ["ACME ROBOTICS — EMPLOYEE HANDBOOK\n", "=" * 40, ""]
    for i, (title, body) in enumerate(_POLICIES, start=1):
        parts.append(f"Section {i}. {title}\n{body}\n")
    # Deterministic appendix to add bulk (facilities directory) — no randomness, so the bytes are
    # identical every run and the cache actually hits.
    parts.append("Appendix A. Facilities directory\n")
    for n in range(1, 121):
        floor = (n % 5) + 1
        parts.append(
            f"Room R-{n:03d}: meeting room on floor {floor}, capacity {4 + (n % 8) * 2}, "
            f"equipped with a display and conferencing hardware; booked via the Facilities portal."
        )
    return "\n".join(parts)


HANDBOOK = build_handbook()

SYSTEM_INSTRUCTIONS = (
    "You are the ACME Robotics HR assistant. Answer employee questions using only the employee "
    "handbook provided below. Be concise, cite the relevant section by name, and if the handbook "
    "does not cover the question, say so. Answer directly from the handbook; do not call tools "
    "unless a question truly requires one."
)

# A simple tool included purely so the cached prefix contains tools + system together (render
# order is tools → system, so the system breakpoint caches both).
NOTE_TOOL = {
    "name": "save_note",
    "description": "Save a short note for the employee to their personal records.",
    "input_schema": {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "The note to save."}},
        "required": ["text"],
    },
}

QUESTIONS = [
    "How many paid vacation days do new employees get, and do they roll over?",
    "What is the remote-work policy and what are the core hours?",
    "How do I submit an expense report, and when do I need receipts?",
    "How often must I rotate my password and how long must it be?",
    "How much parental leave do non-birthing parents receive?",
]


# --------------------------------------------------------------------------- #
# Prompt assembly (caching on/off, plus a deliberate invalidator)
# --------------------------------------------------------------------------- #
def build_system(cache=True, volatile_prefix=None):
    """Build the system blocks.

    With `cache=True`, a single `cache_control` breakpoint on the last (handbook) block caches the
    tools + system + handbook prefix. `volatile_prefix` prepends changing text *before* the
    breakpoint — the classic silent invalidator that defeats caching.
    """
    blocks = []
    if volatile_prefix:
        blocks.append({"type": "text", "text": volatile_prefix})
    blocks.append({"type": "text", "text": SYSTEM_INSTRUCTIONS})
    handbook_block = {"type": "text", "text": HANDBOOK}
    if cache:
        handbook_block["cache_control"] = {"type": "ephemeral"}
    blocks.append(handbook_block)
    return blocks


def build_tools():
    return [NOTE_TOOL]


def ask(client, question, cache=True, volatile_prefix=None, max_tokens=512):
    """Run one question; return (response, elapsed_seconds)."""
    start = time.perf_counter()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=build_system(cache=cache, volatile_prefix=volatile_prefix),
        tools=build_tools(),
        messages=[{"role": "user", "content": question}],
    )
    return response, time.perf_counter() - start


def usage_of(response):
    """Extract the cache-relevant usage fields as a plain dict."""
    u = response.usage
    return {
        "input": getattr(u, "input_tokens", 0) or 0,
        "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
        "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
        "output": getattr(u, "output_tokens", 0) or 0,
    }


def relative_input_cost(usage):
    """Approximate input cost vs. an uncached request of the same prompt (1.0 = no savings).

    Cache reads cost ~0.1x and 5-minute writes ~1.25x base input price; uncached is 1.0x.
    """
    total_prompt = usage["input"] + usage["cache_write"] + usage["cache_read"]
    if total_prompt == 0:
        return 1.0
    effective = usage["input"] + usage["cache_write"] * 1.25 + usage["cache_read"] * 0.1
    return effective / total_prompt


def prefix_token_count(client):
    """Count the tokens in the cacheable prefix (tools + system), to compare against the minimum."""
    result = client.messages.count_tokens(
        model=MODEL,
        system=build_system(cache=False),
        tools=build_tools(),
        messages=[{"role": "user", "content": "placeholder"}],
    )
    return result.input_tokens
