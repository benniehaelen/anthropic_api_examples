# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of **self-contained Anthropic API examples**, each demonstrating one capability of
the Claude Messages API. Examples are Jupyter notebooks (often with a companion Streamlit app
and/or CLI runner) organized **by topic** in top-level folders, one folder per capability —
currently `vision/` (image analysis), `video/` (animal recognition in video), `citations/`
(grounded answers with source citations), and `documents/` (retrieval-augmented search over a
mixed-format document library), with future siblings like `tool-use/` or `prompt-caching/`. Every
example lives under a topic folder; there are no loose example notebooks at the repo root.

Note on documents: the `documents/` topic is RAG — ingest PDF/Word/text/markdown/CSV (`pypdf`,
`python-docx`, plain decode) → chunk → embed with **Voyage AI** → cosine top-k → send the top
passages to Claude as a citable custom-content document → cited answer + ranked passages. The
Anthropic API has **no embeddings endpoint**, which is why retrieval uses Voyage; this topic
therefore needs a **`VOYAGE_API_KEY`** in addition to `ANTHROPIC_API_KEY`. It reuses the
citations pattern (custom-content document → `content_block_location` citations mapped back to the
retrieved passage). Uses `claude-opus-4-8` like `citations/`.

Note on citations: the `citations/` topic enables `citations: {"enabled": True}` on `document`
content blocks; Claude returns text blocks where each block optionally carries a `citations` list
(`cited_text` + `document_index`/`document_title` + a location — char range for plain text, page
range for PDF, block range for custom content). `_citations.py` builds either a plain-text or a
base64-PDF document block per doc (`_document_block`), and renders the response into a footnoted
HTML page (hover-preview + click-to-jump), shown via `st.components.v1.html` in the app. The app
accepts dragged-in `.txt`/`.md`/`.pdf` files (PDFs → page citations, text → char citations);
`.docx`/`.csv`/`.xlsx` are not citable document blocks and must be converted to text first.
Citations are **incompatible with Structured Outputs** (`output_config.format`) — enabling both 400s.

Note on video: the Claude API has **no native video input** — it takes images. The `video/`
topic therefore decodes a clip into sampled, timestamp-labeled frames (OpenCV), sends them as one
ordered image sequence, asks for **strict JSON** per frame, and collapses that into a per-species
timeline in plain Python. The same per-topic shared-module convention applies (`video/_video.py`,
analogous to `vision/_wildlife.py`).

## Environment & commands

- **Python 3.14** via the local venv at `.venv/`. Platform is **Windows / PowerShell** — invoke
  the venv interpreter directly to avoid activation-state issues:
  - Install deps: `.venv\Scripts\python.exe -m pip install -r requirements.txt`
  - Run a script: `.venv\Scripts\python.exe <script.py>`
- The **API key** is read from a `.env` file at the repo root (`ANTHROPIC_API_KEY`) via
  `python-dotenv`; `.env.example` is the template. `.env` is gitignored. The `documents/` topic
  additionally needs `VOYAGE_API_KEY` (Voyage AI embeddings). **Never commit real keys** — only
  `.env.example` with empty placeholders is tracked.
- There is **no test suite or linter** configured yet. Examples are validated by running the
  notebook cells (each API call costs tokens).
- Some topics also ship a **Streamlit app** (`<topic>/<name>_app.py`) as an interactive front
  end for the same analysis. Run one with
  `.venv\Scripts\python.exe -m streamlit run <topic>/<name>_app.py`. To smoke-test that an app
  boots without spending tokens, run it headless (`--server.headless true --server.port <port>`)
  and check `http://localhost:<port>/_stcore/health` returns 200.
- A topic may also ship a **CLI runner** (`<topic>/run_url.py`) that takes a URL or local image
  path and streams the analysis to the terminal — e.g.
  `.venv\Scripts\python.exe vision/run_url.py <url-or-path>`. Like the app, it imports the shared
  `_wildlife` module (Python puts the script's folder on `sys.path`, so no guard is needed). Note
  every real run spends API tokens; compile-check with `py_compile` and exercise `--help` / the
  bad-path error first.

## The shared example pattern

Every notebook follows the same shape established by `wildlife_id.ipynb`. When adding or editing
examples, reuse this convention rather than inventing a new one:

- **Setup cell**: `load_dotenv()`, then `client = Anthropic()` and a `model` string
  (currently `claude-sonnet-4-5`).
- **Helper cell**: small wrappers reused across examples — `add_user_message` /
  `add_assistant_message` (which accept either a raw value or an SDK `Message` and unwrap
  `.content`), `chat(messages, system=, temperature=, tools=, thinking=, ...)` that builds the
  `client.messages.create(**params)` call, and `text_from_message` to concatenate text blocks.
- The API call comes last, printing `text_from_message(response)`.

### Shared per-topic module (`_wildlife.py` pattern)

When a notebook and its Streamlit app would otherwise duplicate the prompt or image helpers,
that content lives in a single underscore-prefixed module beside them (e.g.
`vision/_wildlife.py`) and **both import from it** — there is no duplicated prompt literal.
`vision/_wildlife.py` exports `MODEL`, `PROMPT`, the image-block builders
`url_image_block(url)`, `image_block(path, media_type)` (local file → base64), and
`bytes_image_block(data, media_type)` (raw bytes, e.g. a Streamlit upload → base64), plus the
location helpers `fetch_image_bytes(url)` (download bytes so EXIF can be read locally),
`extract_gps(data)` (parse EXIF GPS → `{lat, lon, maps_url, ...}` or `None`), and
`reverse_geocode(lat, lon)` (coordinates → place-name string via OpenStreetMap Nominatim, or
`None`).

Location is handled two ways, deliberately separated: Claude **estimates** a region from the
pixels (step 5 of `PROMPT`), while **precise** coordinates come only from EXIF metadata, which
the API never exposes — so `extract_gps` reads the file's bytes directly, and `reverse_geocode`
turns them into a place name. Most web images have EXIF stripped, so `None` is the expected
common result. `extract_gps` uses Pillow; `fetch_image_bytes` and `reverse_geocode` use httpx
(both direct dependencies in `requirements.txt`). `reverse_geocode` calls the public Nominatim
service — it sends a descriptive `User-Agent` per their policy (~1 req/sec), needs no API key,
and results are © OpenStreetMap contributors (surface that attribution wherever a place name is
shown).

Import notes:
- The **notebook** can't rely on `__file__`, so its setup cell adds the module's folder to
  `sys.path` (trying both `.` and the topic folder) before `from _wildlife import ...`, so it
  works whether the working directory is the topic folder or the repo root.
- The **Streamlit app** needs no such guard — Streamlit puts the script's own folder on
  `sys.path`, so a plain `from _wildlife import ...` resolves.

**Layout decision (keep helpers flat).** Topic helper modules stay directly in the topic folder
(`vision/_wildlife.py`), *not* in a `helpers/`/`lib/` sub-folder. Colocation keeps imports
trivial and avoids extra `sys.path` handling in notebooks. Do not introduce sub-folders for
helpers at this scale. The generic Anthropic scaffolding (`add_user_message`, `chat`,
`text_from_message`, streaming) is currently copied per consumer; only when a **second topic**
actually needs it should it be lifted into a single top-level shared module — avoid that
abstraction until there is a real second consumer.

## Conventions for new examples

- Place each example at `<topic>/<name>.ipynb` (top-level topic folder, no numeric prefix).
  Reuse an existing topic folder when one fits; otherwise create a new topic folder named after
  the capability. Add a row under the matching topic heading in `README.md` (create the heading
  if new).
- Keep examples runnable with no local assets when possible — prefer public **image URLs**
  (e.g. public-domain NPS/government photos) over committing binary files, and document the
  source and license in a markdown cell.
- Start each notebook with a markdown title cell describing the capability and noting the
  `ANTHROPIC_API_KEY` requirement.
- A Streamlit companion app shares its prompt and image helpers with the notebook through the
  per-topic `_wildlife.py`-style module (see "Shared per-topic module" above) rather than
  copying them, and streams the response via `client.messages.stream`. Name it `<name>_app.py`
  next to the notebook and add a row + run command under the same README topic heading.
