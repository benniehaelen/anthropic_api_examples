# Feature guide — when to reach for what

The certification rewards *judgment*: picking the right feature for a situation. This is a
decision guide across the Claude API features shown in this repo. See [GLOSSARY](GLOSSARY.md) for
terms and [STUDY_GUIDE](STUDY_GUIDE.md) for exam mapping.

## Pick the surface

| If you need… | Use | Why |
| --- | --- | --- |
| One-shot classification, extraction, summarization, Q&A | **Single Messages call** | One request in, one response out |
| The model to *act* — call functions, look things up, take steps | **Tool use** (client tools) | You define tools; Claude calls them in a loop → [`tool_use/`](tool_use/) |
| To run code / analyze data / make files | **Code execution** (server tool) | Anthropic runs it; no client loop → [`code_execution/`](code_execution/) |
| A persisted, server-managed agent with a workspace | **Managed Agents** | Anthropic runs the loop + hosts tools *(not in this repo)* |

Start at the simplest tier that works. Add tools only when the task needs to act; reach for a full
agent only when the trajectory is open-ended.

## Answering over your own data

| Situation | Approach | Topic |
| --- | --- | --- |
| A few documents that fit in context | Put them in the prompt; enable **citations** for attribution | [`citations/`](citations/) |
| A large corpus that won't fit | **RAG**: embed + retrieve top-k, then answer | [`documents/`](documents/) |
| The *same* big context reused across many questions | **Prompt caching** on the document prefix | [`prompt_caching/`](prompt_caching/) |
| You need to prove where an answer came from | **Citations** (`cited_text` + location) | [`citations/`](citations/) |

Rule of thumb: **retrieve when the corpus is large; cache when the context is large *and* reused;
cite when trust matters.** These compose — RAG results can be cited, and a cached prefix can carry
citable documents.

## Constraining the output

| You want… | Use |
| --- | --- |
| A validated object (final answer) | `client.messages.parse(output_format=PydanticModel)` → [`structured_outputs/`](structured_outputs/) |
| Raw JSON to a schema (no Pydantic) | `output_config={"format": {"type": "json_schema", ...}}` |
| Guaranteed-valid *tool arguments* | `"strict": True` on the tool's `input_schema` |
| Grounded citations | `citations: {"enabled": true}` on documents |

**Mutually exclusive:** citations and structured outputs (`output_config.format`) **cannot** be
used together — a 400. Choose grounding *or* a strict output shape per request.

## Server vs client tools

| | Client tool | Server tool (code execution) |
| --- | --- | --- |
| Who runs it | You | Anthropic |
| Loop you write | Yes (`tool_use` → `tool_result`) | No (results come back) |
| Best for | Your APIs, DB lookups, business logic | Data analysis, file generation, computation |
| Topic | [`tool_use/`](tool_use/) | [`code_execution/`](code_execution/) |

## Cost & latency levers

- **Prompt caching** — biggest lever when a large prefix repeats. Reads ~0.1×. Break-even ~2
  requests (5-min TTL). → [`prompt_caching/`](prompt_caching/)
- **Retrieval over stuffing** — send only the relevant chunks, not the whole corpus.
- **Downscale images / sample fewer video frames** — image tokens scale with pixels. → [`vision/`](vision/), [`video/`](video/)
- **Batch API** — ~50% cost for non-latency-sensitive bulk work.
- **`cited_text` is free**; code execution is **free when web search/fetch is in the request**.
- **Model + effort** — use the smallest model that's good enough; tune `effort`.

## Choosing a model (rough guide)

| Model | Lean toward it when… |
| --- | --- |
| **Haiku 4.5** | High volume, latency/cost-sensitive, simpler tasks; a cheap first-pass filter |
| **Sonnet 4.x** | The default workhorse — strong quality at moderate cost (most topics here use Sonnet 4.5) |
| **Opus 4.x** | Hardest reasoning, agentic/coding, or quality-critical work (this repo uses Opus 4.8 for citations/documents) |

Confirm current model IDs, context windows, and **pricing** in the official docs — see
[CHEATSHEET](CHEATSHEET.md) for the limits this repo relies on and links to the source of truth.
