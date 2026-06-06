# Study guide — using this repo for the Claude Certified Architect (CCA) exam

This repository is a **hands-on companion** for studying the Claude API. Each topic folder pairs
a runnable example (notebook + Streamlit app + CLI) with a `LEARN.md` study sheet — learning
objectives, an API cheat-sheet, common pitfalls, exercises, and self-check questions.

> **Unofficial.** This is a community study aid, not an Anthropic product and not endorsed by
> Anthropic. Always confirm exam scope against the official guide on
> [Anthropic's training platform (Skilljar)](https://anthropic.skilljar.com/). Exam details below
> are summarized from public write-ups (linked at the bottom) and may change.

## The exam at a glance

The **Claude Certified Architect (CCA) — Foundations** is a proctored, 60-question exam
(scenario-based; 720/1000 to pass) covering five weighted domains:

| # | Domain | Weight | Covered by this repo? |
|---|--------|:------:|------------------------|
| 1 | **Agentic Architecture** | 27% | ◑ Partially — `code_execution/` (server tool as an agent primitive), `documents/` (RAG pipeline). *Gaps: multi-tool agent loops, Managed Agents.* |
| 2 | **Claude Code Configuration** | 20% | ○ Out of scope — this is about the Claude Code CLI, not the API. See the official courses. |
| 3 | **Prompt Engineering & Structured Output** | 20% | ● `vision/` (multi-step structured-analysis prompt + calibrated confidence), `citations/`. |
| 4 | **Tool Design & MCP Integration** | 18% | ◑ Partially — `code_execution/` (server tool). *Gaps: custom client tools, MCP.* |
| 5 | **Context & Reliability** | 15% | ● `documents/` (retrieval to manage context), `citations/` (grounding/trust), `pause_turn` + prompt-caching patterns throughout. |

● strong · ◑ partial · ○ not covered

This repo is deliberately **API-centric**, so it is strongest on domains 3 and 5, useful for 1
and 4, and intentionally silent on domain 2 (use Anthropic's Claude Code material for that).

## How to study with this repo

1. **Read** the topic's `LEARN.md` (objectives → concepts → cheat-sheet → pitfalls).
2. **Run** the example — notebook for the guided walk-through, the Streamlit app to play, the CLI
   for quick iteration. See the [README](README.md) for setup (`requirements.txt` + `.env`).
3. **Do the exercises** at the bottom of each `LEARN.md` — modify the code, don't just read it.
4. **Self-check** with the questions (answers included) before moving on.

Suggested order (builds from fundamentals to reliability):

1. [`vision/LEARN.md`](vision/LEARN.md) — multimodal input + structured, calibrated prompts
2. [`citations/LEARN.md`](citations/LEARN.md) — grounding answers in sources, trust
3. [`documents/LEARN.md`](documents/LEARN.md) — RAG, retrieval, context management
4. [`code_execution/LEARN.md`](code_execution/LEARN.md) — server tools, the Files API, agent primitives
5. [`video/LEARN.md`](video/LEARN.md) — working within model constraints (no native video), cost/coverage trade-offs

## Cross-cutting themes the exam loves

These show up across domains and across this repo — know them cold:

- **Prompt caching** — prefix stability, `cache_control` placement, what silently invalidates a
  cache (`usage.cache_read_input_tokens` to verify). Used in `citations/` and `documents/`.
- **Citations vs. Structured Outputs** — they are **mutually incompatible** (enabling both 400s).
  A classic "which feature do I reach for" trade-off.
- **Reliability patterns** — `pause_turn` resumption (`code_execution/`), graceful degradation
  (every topic falls back cleanly), cost/coverage trade-offs (`video/` sampling).
- **Server vs. client tools** — code execution is server-side (no tool-result loop you write);
  contrast with client-defined tools you execute and return.
- **Choosing the surface** — single call vs. workflow vs. agent; when retrieval beats stuffing
  context; when to add a second provider (embeddings via Voyage in `documents/`).

## Official resources

- [Anthropic training platform (Skilljar)](https://anthropic.skilljar.com/) — the official courses
- [Claude API documentation](https://platform.claude.com/docs/) — the source of truth for every feature

## Sources for the exam summary

- [Anthropic Skilljar courses](https://anthropic.skilljar.com/)
- [Claude Certified Architect curriculum overview (the-ai-corner.com)](https://www.the-ai-corner.com/p/claude-certified-architect-curriculum-2026)
- [CCA exam: 5 domains, 6 scenarios (dev.to)](https://dev.to/aws-builders/the-claude-certified-architect-exam-5-domains-6-scenarios-and-everything-you-need-to-know-4le3)
