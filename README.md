# Anthropic API examples

[![smoke](https://github.com/benniehaelen/anthropic_api_examples/actions/workflows/ci.yml/badge.svg)](https://github.com/benniehaelen/anthropic_api_examples/actions/workflows/ci.yml)

A growing collection of self-contained examples for the [Anthropic API](https://docs.anthropic.com/),
using the official `anthropic` Python SDK.

> 📚 **Studying for the [Claude Certified Architect](https://anthropic.skilljar.com/) exam?**
> See the [**STUDY_GUIDE**](STUDY_GUIDE.md) — it maps these examples to the exam domains, and each
> topic has a `LEARN.md` with objectives, an API cheat-sheet, pitfalls, exercises, and self-check
> questions.

## Setup

The repo includes a Python 3.14 virtual environment in `.venv/`. On Windows / PowerShell:

```powershell
# Install dependencies into the venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Provide your API key
copy .env.example .env
# then edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

Each example loads the key from `.env` via `python-dotenv`, so you only configure it once. The
`documents/` topic additionally needs a `VOYAGE_API_KEY` (Voyage AI powers retrieval — get one at
[voyageai.com](https://www.voyageai.com/)); every other topic needs only `ANTHROPIC_API_KEY`.

## Study guide

This repo doubles as hands-on prep for the [Claude Certified Architect](https://anthropic.skilljar.com/)
(CCA) exam. The [**STUDY_GUIDE**](STUDY_GUIDE.md) maps each example to the exam's five domains
(with an honest "what's covered vs. not" table) and suggests a study order. Each topic ships a
`LEARN.md` study sheet with learning objectives, an API cheat-sheet, common pitfalls, hands-on
exercises, and self-check questions:
[vision](vision/LEARN.md) ·
[citations](citations/LEARN.md) ·
[documents](documents/LEARN.md) ·
[code execution](code_execution/LEARN.md) ·
[prompt caching](prompt_caching/LEARN.md) ·
[tool use](tool_use/LEARN.md) ·
[structured outputs](structured_outputs/LEARN.md) ·
[agents](agents/LEARN.md) ·
[mcp](mcp/LEARN.md) ·
[video](video/LEARN.md).

Plus repo-wide references: a [**PRACTICE_EXAM**](PRACTICE_EXAM.md) (scenario questions with
answers), a [**FEATURE_GUIDE**](FEATURE_GUIDE.md) (when to reach for what), a
[**GLOSSARY**](GLOSSARY.md), and a [**CHEATSHEET**](CHEATSHEET.md) (limits, costs, defaults).

The study material is an unofficial community aid — confirm exam scope against the official guide
on [Anthropic's training platform](https://anthropic.skilljar.com/).

## Contributing

New topics are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the repo's shape (one
top-level folder per capability: a shared `_<topic>.py` module + notebook + optional app/CLI +
`LEARN.md`) and the add-a-topic checklist. Run the offline smoke test before a PR:
`.venv\Scripts\python.exe tests/smoke_test.py` (CI runs it on every push/PR).

## Examples

Examples are organized into top-level topic folders, one per Claude API capability. Open a
notebook with Jupyter (or the VS Code notebook editor) and run the cells top to bottom.

### Vision

📚 Study sheet: [`vision/LEARN.md`](vision/LEARN.md)

| Example | Description |
| --- | --- |
| [`vision/wildlife_id.ipynb`](vision/wildlife_id.ipynb) | Identify wildlife in a photo with Claude's vision capability — subject detection, species ID, look-alikes, habitat cues, a region estimate, and a 1-4 confidence rating. Also reads precise GPS coordinates from the photo's EXIF metadata when present and resolves them to a place name. Works with a public image URL or a local file. |
| [`vision/wildlife_id_app.py`](vision/wildlife_id_app.py) | A Streamlit front end for the wildlife analysis above: paste an image URL or drag in a photo, watch the analysis stream in, and see the confidence rating as a color-coded badge plus a location card (EXIF GPS coordinates + place name when available, Claude's inferred region otherwise). |
| [`vision/run_url.py`](vision/run_url.py) | A command-line runner for the same analysis: pass a URL or local image path, stream the result to your terminal, and print the location (EXIF GPS + place name, or a note that none is present). |

Run the Streamlit app (from the repo root):

```powershell
.venv\Scripts\python.exe -m streamlit run vision/wildlife_id_app.py
```

Or run a single image from the command line:

```powershell
.venv\Scripts\python.exe vision/run_url.py https://example.com/photo.jpg
.venv\Scripts\python.exe vision/run_url.py my_photo.jpg --no-location
```

Place names are resolved with the [OpenStreetMap Nominatim](https://nominatim.org/) service
(no API key required) and are © OpenStreetMap contributors. Nominatim asks callers to stay
under ~1 request/second; for heavy use, run your own instance or a paid geocoder.

### Video

The Claude API takes images, not video — so these examples decode a clip into sampled,
timestamp-labeled frames, analyze them as one sequence, and report a per-species timeline.
Frame decoding uses OpenCV.

📚 Study sheet: [`video/LEARN.md`](video/LEARN.md)

| Example | Description |
| --- | --- |
| [`video/animal_video_id.ipynb`](video/animal_video_id.ipynb) | Identify animals across a short video: sample frames at a fixed interval, send them to Claude as one ordered sequence, and collapse the per-frame JSON into a per-species timeline (first/last seen, frames, max count). |
| [`video/run_video.py`](video/run_video.py) | A command-line runner for the same analysis: pass a video URL or local path, and print the summary plus the per-species timeline. |

Run a video from the command line (from the repo root):

```powershell
.venv\Scripts\python.exe video/run_video.py clip.mp4
.venv\Scripts\python.exe video/run_video.py https://example.com/clip.mp4 --every-sec 0.5 --max-frames 30
.venv\Scripts\python.exe video/run_video.py clip.mp4 --longest-side 1280   # more frame detail, more tokens
```

Frames are downscaled to `--longest-side` pixels (default 768) to control image-token cost.
Raising it gives the model more detail, but it can't compensate for a subject that is small or
occluded in the frame — for hard species IDs, cropping the animal before sending it is far more
effective than raising global resolution.

### Citations

Claude's Citations feature grounds an answer in documents you provide and returns the exact
source text for each claim. These examples render that as a footnoted article — hover a marker
to preview the cited source, click to jump to the reference.

📚 Study sheet: [`citations/LEARN.md`](citations/LEARN.md)

| Example | Description |
| --- | --- |
| [`citations/citations_demo.ipynb`](citations/citations_demo.ipynb) | Walk through the Citations API: build citable document blocks, ask a question, inspect the citation objects (`cited_text`, document index/title, char/page/block locations), and render the cited answer. |
| [`citations/citation_app.py`](citations/citation_app.py) | A Streamlit app: drag in documents (`.txt`, `.md`, `.pdf`) or edit text inline, ask a question, and Claude's grounded answer renders with hover-preview footnotes and click-to-jump references. PDFs cite by page, text by character range. Ships with a wildlife knowledge base. |

Run the Streamlit app (from the repo root):

```powershell
.venv\Scripts\python.exe -m streamlit run citations/citation_app.py
```

### Documents (search a library)

Retrieval-augmented search over a library of mixed-format documents. The Anthropic API has no
embeddings endpoint, so retrieval uses **Voyage AI** (the provider Anthropic recommends); Claude
then answers from the top passages with citations. Returns both the cited answer and the ranked
passages. **Requires `VOYAGE_API_KEY`** (in addition to `ANTHROPIC_API_KEY`) — get one at
[voyageai.com](https://www.voyageai.com/).

📚 Study sheet: [`documents/LEARN.md`](documents/LEARN.md)

| Example | Description |
| --- | --- |
| [`documents/document_search.ipynb`](documents/document_search.ipynb) | Walk through the pipeline: ingest PDF/Word/text/markdown/CSV, chunk, embed with Voyage, retrieve top-k by cosine similarity, and have Claude answer with citations to the passages. |
| [`documents/search_app.py`](documents/search_app.py) | A Streamlit app: drag in a set of documents, type a query, and see Claude's cited answer plus the ranked passages with similarity scores. |
| [`documents/run_search.py`](documents/run_search.py) | A command-line runner: point it at files or a folder, pass `--query`, and print the answer + ranked passages (optionally write the cited result to HTML with `--out`). |

```powershell
.venv\Scripts\python.exe -m streamlit run documents/search_app.py
.venv\Scripts\python.exe documents/run_search.py ./docs --query "..." --k 8 --out answer.html
```

### Code execution

Claude writes and runs Python/Bash in a secure sandbox on Anthropic's servers (a *server tool* —
no client-side tool loop). Upload data via the Files API, and Claude can clean it, analyze it, and
produce files (e.g. charts) you download back. Sandbox: Python 3.11, ~5 GiB RAM, no internet,
pandas/numpy/matplotlib/scikit-learn preinstalled.

📚 Study sheet: [`code_execution/LEARN.md`](code_execution/LEARN.md)

| Example | Description |
| --- | --- |
| [`code_execution/code_execution.ipynb`](code_execution/code_execution.ipynb) | End-to-end: a warm-up calculation, then generate a messy sales CSV, upload it, have Claude clean it and render a bar chart, and download the chart. |
| [`code_execution/code_app.py`](code_execution/code_app.py) | A Streamlit sandbox: upload a data file (or use the built-in sample), describe a task, and see Claude's narrative, the code it ran, the output, and the files it produced (charts inline). |
| [`code_execution/run_code.py`](code_execution/run_code.py) | A command-line runner: pass `-p "<task>"` (and optionally `-f data.csv` or `--sample`), print the transcript, and save any files Claude creates. |

```powershell
.venv\Scripts\python.exe -m streamlit run code_execution/code_app.py
.venv\Scripts\python.exe code_execution/run_code.py -p "Clean and chart this data" --sample
```

### Prompt caching

Reuse a large, stable prompt prefix across requests to cut input cost (~0.1× on cache reads) and
latency. These examples cache a sizable document + system prompt + tool, then **measure** the
savings via the `usage` fields — and show the classic "silent invalidator" that breaks caching.

📚 Study sheet: [`prompt_caching/LEARN.md`](prompt_caching/LEARN.md)

| Example | Description |
| --- | --- |
| [`prompt_caching/caching_demo.ipynb`](prompt_caching/caching_demo.ipynb) | Walk through caching: confirm the prefix clears the model minimum, watch the first call write and later calls read (`cache_creation_input_tokens` vs `cache_read_input_tokens`), measure the savings, and break it on purpose with a volatile prefix. |
| [`prompt_caching/cache_app.py`](prompt_caching/cache_app.py) | A Streamlit "cache lab": run a batch of questions, chart per-request cache-read vs write vs full-price tokens, and toggle caching / a volatile prefix to see the effect. |
| [`prompt_caching/run_cache.py`](prompt_caching/run_cache.py) | A command-line demo; `--compare` runs the batch uncached then cached and reports how much of the prompt moved to ~0.1× price. |

```powershell
.venv\Scripts\python.exe -m streamlit run prompt_caching/cache_app.py
.venv\Scripts\python.exe prompt_caching/run_cache.py --compare
```

### Tool use

Custom (client) tools: you declare tools, Claude decides when to call them, **you** run them and
feed results back in a loop. The opposite of the code-execution *server* tool. Shows the manual
agentic loop, the SDK tool runner, `tool_choice`, and `is_error` recovery.

📚 Study sheet: [`tool_use/LEARN.md`](tool_use/LEARN.md)

| Example | Description |
| --- | --- |
| [`tool_use/tool_use.ipynb`](tool_use/tool_use.ipynb) | A single tool call by hand, the manual agentic loop over two tools (calculator + weather), the automatic `@beta_tool` tool runner, and `tool_choice` / error handling. |
| [`tool_use/agent_app.py`](tool_use/agent_app.py) | A Streamlit agent: ask a question and watch the loop — each tool call, its result, and the final answer. |
| [`tool_use/run_agent.py`](tool_use/run_agent.py) | A command-line agent that prints the transcript and final answer. |

```powershell
.venv\Scripts\python.exe -m streamlit run tool_use/agent_app.py
.venv\Scripts\python.exe tool_use/run_agent.py -q "Weather in Tokyo, and 100 - 32?"
```

### Structured outputs

Make Claude return schema-valid data you can use without parsing. Uses `messages.parse` with a
Pydantic model (validated objects), the raw `output_config.format` JSON schema, and `strict: True`
tools. The example extracts structured wildlife sighting records from messy free-text field notes.

📚 Study sheet: [`structured_outputs/LEARN.md`](structured_outputs/LEARN.md)

| Example | Description |
| --- | --- |
| [`structured_outputs/structured_outputs.ipynb`](structured_outputs/structured_outputs.ipynb) | `messages.parse` → validated objects, batch extraction into a table, the raw `output_config.format` path, strict tool use, and the citations-incompatibility constraint. |
| [`structured_outputs/extract_app.py`](structured_outputs/extract_app.py) | A Streamlit extractor: paste field notes, get a clean table of schema-valid records (downloadable as JSON). |
| [`structured_outputs/run_extract.py`](structured_outputs/run_extract.py) | A command-line extractor over a notes file or the built-in sample. |

```powershell
.venv\Scripts\python.exe -m streamlit run structured_outputs/extract_app.py
.venv\Scripts\python.exe structured_outputs/run_extract.py --sample
```

### Agents

A self-correcting, multi-agent data analyst — the repo's agentic capstone. An **orchestrator**
decomposes a question, **analyst** agents write and run code to answer each part, a **critic**
reviews each finding and sends weak ones back for revision, and a **synthesizer** writes the final
report. Shows decomposition/fan-out, the act→critique→revise self-correction loop, structured
hand-offs, and bounded loops. (Makes several API calls per run — keep the caps low.)

📚 Study sheet: [`agents/LEARN.md`](agents/LEARN.md)

| Example | Description |
| --- | --- |
| [`agents/analyst.ipynb`](agents/analyst.ipynb) | Walk the loop: orchestrator plan → analyst (code execution) ⇄ critic (structured verdict) → synthesizer, over a generated dataset with planted data-quality issues. |
| [`agents/analyst_app.py`](agents/analyst_app.py) | A Streamlit app that streams the multi-agent trace live, then renders the final report. |
| [`agents/run_analyst.py`](agents/run_analyst.py) | A command-line agent over your CSV (or the built-in sample). |

```powershell
.venv\Scripts\python.exe -m streamlit run agents/analyst_app.py
.venv\Scripts\python.exe agents/run_analyst.py --sample
```

### MCP (Model Context Protocol)

Connect Claude to an external **tool server** via the open MCP standard. This topic runs a small
**local MCP server** as a subprocess (stdio) and lets Claude use its tools through the SDK's MCP
helpers + tool runner — then documents the remote `mcp_servers` alternative. Needs
`pip install "anthropic[mcp]" mcp`. (The MCP client path is async, so this topic has a notebook +
CLI, no Streamlit app.)

📚 Study sheet: [`mcp/LEARN.md`](mcp/LEARN.md)

| Example | Description |
| --- | --- |
| [`mcp/server.py`](mcp/server.py) | A self-contained MCP server (FastMCP) exposing a few wildlife tools over stdio. |
| [`mcp/mcp_demo.ipynb`](mcp/mcp_demo.ipynb) | Spawn the server, list its tools, and watch Claude call them via the tool runner; plus local-vs-remote MCP. |
| [`mcp/run_mcp.py`](mcp/run_mcp.py) | A command-line demo that runs a query through the local MCP server and prints which tools were called. |

```powershell
.venv\Scripts\python.exe mcp/run_mcp.py -q "Compare the red fox and gray wolf, with sighting counts."
```
