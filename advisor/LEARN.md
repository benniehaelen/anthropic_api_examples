# Learn — Advisor tool (executor + advisor pairing)

A study sheet for the `advisor/` example. Pair it with the notebook
([`advisor_demo.ipynb`](advisor_demo.ipynb)) and the CLI ([`run_advisor.py`](run_advisor.py)).

**Where this fits in the CCA exam:** primarily **Context & Reliability** (15%) — a cost/quality
optimization with explicit governance — and **Agentic Architecture** (27%), since it orchestrates
two models inside one request. See the [STUDY_GUIDE](../STUDY_GUIDE.md).

> **Beta:** requires the `advisor-tool-2026-03-01` header, and access may be gated — confirm your
> key can call it. Available on the Claude API and Claude Platform on AWS; not on Bedrock, Vertex
> AI, or Microsoft Foundry. Verify current status in the
> [official docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool).

## Learning objectives

- Explain when the executor-advisor pattern pays off (long-horizon agentic work where most turns
  are mechanical but the plan matters) and when it doesn't (single-turn Q&A, pass-through model
  pickers, workloads where every turn needs full advisor capability).
- Construct a valid executor-advisor pair and predict the 400 for an invalid one.
- Walk the response anatomy: `server_tool_use` (empty input) → `advisor_tool_result` (one of three
  content variants).
- Bound advisor cost three ways: `max_tokens` on the tool (hard, per call), `max_uses` (hard, per
  request), and a client-side counter with history cleanup (conversation level).
- Read `usage.iterations[]` and explain why advisor tokens aren't in the top-level totals.

## Key concepts

- **One request, two models.** The top-level `model` is the **executor**; the `model` inside the
  tool definition is the **advisor**. The executor decides *when* to consult; Anthropic runs the
  advisor server-side over the executor's full transcript and returns advice — no extra round trip.
- **The advisor's input is always empty.** The server builds the advisor's view from the
  transcript; nothing the executor writes into the tool input reaches the advisor.
- **Guide vs. govern** (the architect's lens): the system prompt and the user-message brevity line
  *guide* (soft — the model can deviate); `max_tokens` (per call), `max_uses` (per request), and
  the client-side conversation cap *govern* (hard). The strongest configs use the brevity line
  **and** a `max_tokens` cap together.
- **Billing is split.** Advisor tokens bill at the advisor model's rates, so they're **not** rolled
  into the top-level usage. The full breakdown is `usage.iterations[]` (`message` = executor,
  `advisor_message` = advisor).

## API cheat-sheet

| Item | Value |
| --- | --- |
| Beta header | `advisor-tool-2026-03-01` (via `betas=[...]` on `client.beta.messages.create`) |
| Tool def | `{"type": "advisor_20260301", "name": "advisor", "model": "<advisor model>"}` |
| Valid pairs | Advisor ≥ executor in capability (e.g. Sonnet 4.6 executor + Opus 4.8 advisor). **Sonnet 4.5 is not a valid executor** — use Sonnet 4.6+. Invalid pairs → 400 |
| Tool input | Always empty; the server forwards the transcript |
| Result variants | `advisor_result` (`text`, `stop_reason`), `advisor_redacted_result` (`encrypted_content`, round-trip verbatim), `advisor_tool_result_error` (`error_code`) |
| Advisor output cap | `max_tokens` on the tool (min 1024, start at 2048); truncation → `stop_reason: "max_tokens"` |
| Per-request cap | `max_uses` on the tool |
| Conversation cap | None built in — count client-side, then remove the tool **and** strip advisor blocks (else 400) |
| Advisor caching | `caching: {"type":"ephemeral","ttl":"5m"|"1h"}`; break-even ≈ 3 advisor calls |
| Billing | `usage.iterations[]`: `message` (executor rates) / `advisor_message` (advisor rates) |

## Common pitfalls

1. **Top-level `max_tokens` does not bound the advisor.** It caps executor output only — budget by
   it and you under-count advisor spend. Cap the advisor with `max_tokens` on the tool.
2. **Top-level usage excludes advisor tokens.** Cost dashboards must read `usage.iterations[]`.
3. **Dropping the tool without cleaning history → 400.** When capping mid-conversation, also strip
   the `advisor_tool_result` blocks.
4. **The advisor input is not a channel.** Don't design prompts that "send" the advisor a question
   through input — it's always empty; the server forwards the transcript.
5. **Caching below ~3 calls loses money** (the write outweighs one or two reads).
6. **`clear_thinking` with `keep` other than `"all"`** silently degrades advisor cache hits (cost,
   not quality).
7. **Coding tasks under-call the advisor** without system-prompt steering — prepend the timing
   guidance.
8. **Redacted results must be round-tripped verbatim;** branch on `content.type` if you switch
   advisor models mid-conversation.

## Try it yourself

1. Run `run_advisor.py --compare` on a planning-heavy task and on a one-line factual question.
   Explain the difference in advisor-call counts and why the second is a poor fit.
2. Set `--advisor-max-tokens 1024`, find a task that hits `stop_reason: "max_tokens"`, and decide
   whether to raise the cap or proceed with partial advice.
3. Implement a conversation-level cap of two advisor calls with `count_advisor_calls` +
   `strip_advisor_blocks`, and confirm the next request still succeeds after the tool is removed.
4. Build a per-request cost report from `usage.iterations[]` with current model rates, comparing
   executor-alone vs. executor-plus-advisor on the same task.
5. Enable `--caching 5m` on a task with three or more advisor calls and confirm
   `cache_read_input_tokens` becomes non-zero on later `advisor_message` iterations.

## Check yourself

1. **Why is the advisor tool's input always empty, and how does the advisor get its context?**
   <details><summary>Answer</summary>The server builds the advisor's view from the executor's full
   transcript (system prompt, all turns, all tool results). Nothing in the executor's tool input
   reaches the advisor — the executor only signals *when* to consult.</details>

2. **Your bill shows more advisor spend than the top-level usage suggested. What did the dashboard
   read, and what should it have read?**
   <details><summary>Answer</summary>It read top-level `usage` (executor tokens only). It should
   read `usage.iterations[]` and sum the `advisor_message` iterations at the advisor's rates.</details>

3. **A follow-up turn returns 400 after you removed the advisor tool to save cost. What did you
   forget?**
   <details><summary>Answer</summary>To strip the `advisor_tool_result` (and the advisor
   `server_tool_use`) blocks from the message history. History with advisor blocks but no advisor
   tool defined is a 400. Use `strip_advisor_blocks`.</details>

4. **When does advisor-side caching break even, and what setting can silently erode it?**
   <details><summary>Answer</summary>Around three advisor calls per conversation. `clear_thinking`
   with a `keep` value other than `"all"` shifts the advisor's quoted transcript and causes
   advisor-side cache misses (a cost issue, not a quality one).</details>

5. **Which cost control is soft, and which are hard?**
   <details><summary>Answer</summary>Soft: the system-prompt timing guidance and the user-message
   brevity line. Hard: `max_tokens` on the tool (per call), `max_uses` (per request), and the
   client-side conversation cap you enforce.</details>

6. **Name two workload shapes where the advisor pattern is a poor fit.**
   <details><summary>Answer</summary>Single-turn Q&A (nothing to plan), pure pass-through model
   pickers, and workloads where every turn genuinely needs the advisor model's full capability.</details>

## Files

| File | Purpose |
| --- | --- |
| `_advisor.py` | Shared module: tool builder, runner, block extraction, usage summary, conversation-cap helpers |
| `advisor_demo.ipynb` | Walkthrough: quick start, blocks, hard/soft controls, iterations, multi-turn, the conversation cap, caching |
| `run_advisor.py` | CLI: run a task advised, `--compare` against executor-alone, optional `--rates` cost estimate |

## Further reading

- [Advisor tool — Claude API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool)
- [Tool use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
