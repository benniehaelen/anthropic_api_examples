# Learn — Prompt caching

A study sheet for the `prompt_caching/` example. Pair it with the notebook
([`caching_demo.ipynb`](caching_demo.ipynb)), the Streamlit "cache lab"
([`cache_app.py`](cache_app.py)), and the CLI ([`run_cache.py`](run_cache.py)).

**Where this fits in the CCA exam:** primarily **Context & Reliability** (15%) — cost and latency
optimization is a core production concern, and prompt caching is the lever. It's also a
**cross-cutting theme** that shows up wherever you reuse a large prefix (RAG, agents, few-shot).
See the [STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

- Explain the **prefix-match** model and why one byte change invalidates everything after it.
- Place `cache_control` breakpoints correctly given the `tools → system → messages` render order.
- Read the `usage` fields to **prove** caching worked.
- Recognize and fix **silent invalidators**, and recall the model-dependent minimum and economics.

## Key concepts

- **Prefix match.** The cache key is the exact rendered bytes up to each `cache_control`
  breakpoint. Change anything before it (a tool, a system byte, a reordered JSON key) → miss.
- **Render order is `tools` → `system` → `messages`.** A breakpoint on the **last system block**
  caches tools + system together. Put volatile content *after* the last breakpoint.
- **Measure with `usage`:**
  - `cache_creation_input_tokens` — written this request (the ~1.25x write premium, 5-min TTL).
  - `cache_read_input_tokens` — served from cache (~0.1x).
  - `input_tokens` — the full-price remainder. *Total prompt = sum of all three.*
- **Minimum cacheable prefix is model-dependent:** 1024 (Sonnet 4.5) · 2048 (Sonnet 4.6) · 4096
  (Opus 4.x, Haiku 4.5). Below it, caching **silently** no-ops (`cache_creation_input_tokens: 0`).
- **Economics / TTL:** reads ~0.1x; writes 1.25x (5-min, default) or 2x (1-hour,
  `{"type":"ephemeral","ttl":"1h"}`). 5-min TTL breaks even at ~2 requests.
- **Up to 4 breakpoints** per request. Caches are **model-scoped** (switching model = full miss).

## API cheat-sheet

```python
resp = client.messages.create(
    model="claude-sonnet-4-5", max_tokens=512,
    system=[
        {"type": "text", "text": SYSTEM_PROMPT},
        {"type": "text", "text": BIG_STABLE_DOC, "cache_control": {"type": "ephemeral"}},  # breakpoint
    ],
    tools=TOOLS,                                   # rendered before system → cached by the marker above
    messages=[{"role": "user", "content": question}],   # volatile question, after the prefix
)
u = resp.usage
print(u.cache_creation_input_tokens, u.cache_read_input_tokens, u.input_tokens)
```

## Common pitfalls (silent invalidators)

- **A timestamp / UUID / request id in the system prompt** → the prefix changes every request;
  `cache_read` is always 0. Move it into a later `messages` block.
- **Non-deterministic serialization** — `json.dumps(d)` without `sort_keys=True`, iterating a
  `set`, an unsorted tool list. Same bytes every time or no cache.
- **Changing tools or model mid-conversation** — tools render at position 0; any change rebuilds
  everything. Caches are also per-model.
- **Marking the end of the *whole* prompt** instead of the end of the *shared* prefix — then every
  request writes a unique entry and nothing is ever read. Mark the end of the shared part.
- **Too-short prefix** — under the model minimum it silently won't cache. Check the token count.
- **Expecting a cross-request read on parallel fan-out** — a cache entry is only readable after
  the first response starts streaming; N simultaneous requests all pay to write.

## Try it yourself

1. **Write → read.** Run the notebook's three calls and confirm call #1 shows `cache_write` and
   call #2 (a different question) shows `cache_read` with `input` collapsing to the question size.
2. **Break it on purpose.** Flip the app's "inject volatile prefix" toggle (or pass `--volatile`)
   and watch `cache_read` drop to 0 on every request.
3. **Model minimum.** Switch `MODEL` in `_prompt_caching.py` to `claude-opus-4-8` and shrink the
   handbook below 4096 tokens — caching silently stops even though the marker is still there.
4. **Compare.** Run `run_cache.py --compare` and read off how much of the prompt moved to ~0.1x.

## Check yourself

1. **You added `cache_control` but `cache_read_input_tokens` is always 0. First thing to check?**
   <details><summary>Answer</summary>A silent invalidator in the prefix — most often a timestamp,
   UUID, or non-deterministic JSON before the breakpoint. Diff the rendered prompt bytes between
   two requests. (Also check the prefix exceeds the model's minimum.)</details>

2. **Where should a per-request timestamp go so it doesn't wreck caching?**
   <details><summary>Answer</summary>After the last breakpoint — in a `messages` block, not the
   system prompt. Content at turn N invalidates nothing before turn N.</details>

3. **Which three `usage` fields describe caching, and how do they relate?**
   <details><summary>Answer</summary>`cache_creation_input_tokens` (written, ~1.25x),
   `cache_read_input_tokens` (read, ~0.1x), `input_tokens` (uncached, 1.0x). Total prompt size is
   their sum.</details>

4. **A 3,000-token prefix caches in your tests on Sonnet 4.5 but not after switching to Opus 4.8.
   Why?**
   <details><summary>Answer</summary>The minimum cacheable prefix is model-dependent: 1024 on
   Sonnet 4.5 but 4096 on Opus 4.8. 3,000 tokens is below Opus's minimum, so it silently won't
   cache. (Caches are also model-scoped, so the switch itself is a fresh start.)</details>

## Further reading

- [Prompt caching — Claude API docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
