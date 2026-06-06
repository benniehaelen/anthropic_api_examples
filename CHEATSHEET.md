# Cheat-sheet — limits, costs & defaults

Quick reference for the numbers and rules this repo relies on. **Pricing and exact limits change**
— this lists what's stable and points to the official source of truth for the rest.

> Always confirm current **pricing**, rate limits, and model specs at
> [platform.claude.com/docs](https://platform.claude.com/docs/) and the Anthropic pricing page.
> This sheet deliberately avoids quoting dollar figures, which go stale.

## Models (this repo)

| Model | Model ID | Context window |
| --- | --- | --- |
| Claude Opus 4.8 | `claude-opus-4-8` | 1M |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M |
| Claude Sonnet 4.5 | `claude-sonnet-4-5` | 1M |
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K |

This repo uses **Sonnet 4.5** for most topics and **Opus 4.8** for `citations/` and `documents/`.
Use exact ID strings (no date suffixes). Caches are **model-scoped** — switching models is a full
cache miss.

## `max_tokens` defaults

- Non-streaming: ~**16K** keeps you under SDK HTTP timeouts.
- Streaming: ~**64K** (timeouts aren't a concern; give the model room).
- Classification/short outputs: a few hundred.
- 128K output (Opus 4.x) **requires streaming**.

## Prompt caching

- **Reads ~0.1×** input price; **writes 1.25×** (5-min TTL) or **2×** (1-hour, `{"ttl":"1h"}`).
  Break-even ≈ 2 requests at 5-min TTL.
- **Minimum cacheable prefix (model-dependent):**

  | Model | Minimum |
  | --- | ---: |
  | Opus 4.x, Haiku 4.5 | 4096 tokens |
  | Sonnet 4.6 | 2048 tokens |
  | Sonnet 4.5 | 1024 tokens |

  Below the minimum it **silently** won't cache (`cache_creation_input_tokens: 0`).
- **Max 4 breakpoints** per request. Render order `tools → system → messages`; a breakpoint on the
  last system block caches tools + system.
- Verify with `usage`: `cache_creation_input_tokens` (write), `cache_read_input_tokens` (read),
  `input_tokens` (uncached remainder). Total prompt = the sum. → [`prompt_caching/`](prompt_caching/)

## Vision

- Formats: JPEG, PNG, GIF, WebP. Image tokens ≈ **(width × height) / 750**.
- Downscale to ~**1568 px** on the long edge — bigger costs more without helping recognition.
- Exact size/resolution/count limits: see the vision docs. → [`vision/`](vision/)

## Code execution

- **Free when `web_search`/`web_fetch` is in the same request**; otherwise billed by execution
  time (5-min minimum per session). **Attaching a file preloads the container, so time is billed
  even if no code runs.**
- Sandbox: Python 3.11, ~5 GiB RAM, **no internet**, pandas/numpy/matplotlib/scikit-learn
  preinstalled. → [`code_execution/`](code_execution/)
- Tool versions: `code_execution_20250825` (all current models) / `code_execution_20260120`
  (REPL state + programmatic tool calling; Opus 4.5+/Sonnet 4.5+).

## Citations & structured outputs

- Citations: enable **all-or-none** across documents; `cited_text` is **free** (not billed as
  output, nor input on later turns). Locations: char (text) / page (PDF) / block (custom).
- Structured outputs: strict JSON schema requires `additionalProperties: false` + `required`, and
  **does not support numeric `minimum`/`maximum`** (use `enum`).
- **Citations + structured outputs together → 400.** Mutually exclusive.

## Other

- **Batch API** — asynchronous, ~**50% cost**, for non-latency-sensitive bulk work.
- **Embeddings** — the Anthropic API has **none**; use **Voyage AI** (`VOYAGE_API_KEY`). Voyage:
  ≤1000 texts/call; `input_type` = `"query"` vs `"document"`. → [`documents/`](documents/)
- **Effort / thinking** — `output_config.effort` (`low`…`max`); Opus 4.7/4.8 use **adaptive
  thinking** only (`thinking: {type: "adaptive"}`).
