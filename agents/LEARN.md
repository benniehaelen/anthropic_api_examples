# Learn — Agents (self-correcting, multi-agent analyst)

A study sheet for the `agents/` example. Pair it with the notebook
([`analyst.ipynb`](analyst.ipynb)), the Streamlit app ([`analyst_app.py`](analyst_app.py)), and
the CLI ([`run_analyst.py`](run_analyst.py)).

**Where this fits in the CCA exam:** **Agentic Architecture** (27% — the largest domain), with
ties to **Tool Design** (the analyst's code-execution action), **Context & Reliability** (the
self-correction loop, bounded iteration), and **Prompt Eng. & Structured Output** (structured
hand-offs). See the [STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

- Decompose a goal into independent sub-tasks (orchestration / fan-out).
- Build a **self-correction loop**: an analyst acts, a critic verifies, the analyst revises.
- Use **structured hand-offs** between agents and keep the context small.
- Make agent loops **reliable**: bounded iterations, error handling, graceful "unverified."

## Key concepts

- **Roles, not one mega-prompt.** Four specialized agents, each a focused Claude call:
  *orchestrator* (plan), *analyst* (act via code execution), *critic* (verify), *synthesizer*
  (combine). Specialization beats asking one prompt to do everything.
- **Deterministic orchestration.** The control flow (loop, fan-out, caps) is plain Python; the
  model supplies reasoning at each step. You decide *when* to call *whom*.
- **Self-correction loop.** `analyst → critic → (revise) → …` until the critic passes or a cap is
  hit. The critic is a *different* agent with a reviewer prompt — it catches what the analyst
  won't catch about itself.
- **Structured hand-offs.** The orchestrator returns a `Plan` and the critic a `Verdict` (Pydantic
  via `messages.parse`), so branching on their output is clean and safe.
- **The action is a tool.** Here the analyst's action is the **code-execution server tool** —
  write + run Python over the uploaded dataset. Swap in client tools for other agents.
- **Context discipline.** Only a finding + its computed output flow downstream — not whole
  transcripts — so the window stays small (and cacheable).

## Architecture

```
question + dataset
   │  ORCHESTRATOR (Plan: list of sub-analyses)
   ▼
for each sub-analysis  ── fan out ──►  ANALYST (runs code) ──► finding
                                          ▲                      │
                                          └── revise ◄── CRITIC (Verdict: passed?)
                                                              │ pass
                                                              ▼
                                                       verified findings
   │  SYNTHESIZER
   ▼
final report
```

## Common pitfalls

- **Unbounded loops.** Always cap revisions *and* sub-tasks, or a stubborn critic loops forever.
- **A critic that's too harsh.** If it demands exhaustiveness, nothing passes and you burn tokens.
  Scope it to "correct and supported," not "perfect." (This example was tuned for exactly that.)
- **The actor not actually acting.** A code-running agent may "explore" (`ls`) and stop —
  instruct it to compute and **print results in one turn**, and check that real output came back.
- **Context blowup.** Don't forward full transcripts between agents; pass only the distilled
  finding/verdict.
- **Cost.** Multi-agent + self-correction means many calls (plan + analyst/critic × sub-tasks ×
  attempts + synthesis). Keep caps low; cache the shared prompt; use a smaller model where it's
  good enough.

## Try it yourself

1. **Watch it self-correct:** run `run_analyst.py --sample` and read the trace — note where the
   critic passes vs. sends a finding back.
2. **Tighten the critic:** make `run_critic`'s prompt stricter and watch revisions (and cost) rise.
3. **Your data:** point the app at your own CSV and question.
4. **Go parallel:** run the sub-analyses concurrently (threads) instead of sequentially.
5. **Stronger verification:** let the critic *run its own code* to check the analyst's numbers,
   instead of reasoning over the printed output.

## Check yourself

1. **Why split the work across multiple agents instead of one big prompt?**
   <details><summary>Answer</summary>Specialized roles stay focused, and an independent critic
   catches errors the analyst won't catch about its own work. Decomposition (fan-out) also keeps
   each step's context small.</details>

2. **What makes this "self-correcting," and what keeps it from looping forever?**
   <details><summary>Answer</summary>The analyst ⇄ critic revision loop: the critic verifies and
   the analyst revises on failure. A revision cap (and a sub-task cap) guarantees termination.</details>

3. **Why return `Plan`/`Verdict` as structured (Pydantic) objects?**
   <details><summary>Answer</summary>So the orchestration code can branch reliably on the model's
   output (e.g. `verdict.passed`) without parsing prose — a clean, safe hand-off between agents.</details>

4. **What's the analyst's "action," and how does context stay small across the loop?**
   <details><summary>Answer</summary>The action is the code-execution server tool (write/run
   Python). Only the distilled finding + computed output flow to the critic and synthesizer — not
   full transcripts.</details>

## Further reading

- [Agent design — building effective agents](https://www.anthropic.com/research/building-effective-agents)
- [Tool use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Code execution tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)
