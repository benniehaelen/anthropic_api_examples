# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of **self-contained Anthropic API examples**, each demonstrating one capability of
the Claude Messages API. Examples are Jupyter notebooks organized **by topic** in top-level
folders, one folder per capability (e.g. `vision/`, and future siblings like `tool-use/`,
`prompt-caching/`, `extended-thinking/`). Every example lives under a topic folder — there are
no loose example notebooks at the repo root. The first example is
`vision/wildlife_id.ipynb` (image analysis).

## Environment & commands

- **Python 3.14** via the local venv at `.venv/`. Platform is **Windows / PowerShell** — invoke
  the venv interpreter directly to avoid activation-state issues:
  - Install deps: `.venv\Scripts\python.exe -m pip install -r requirements.txt`
  - Run a script: `.venv\Scripts\python.exe <script.py>`
- The **API key** is read from a `.env` file at the repo root (`ANTHROPIC_API_KEY`) via
  `python-dotenv`; `.env.example` is the template. `.env` is gitignored.
- There is **no test suite or linter** configured yet. Examples are validated by running the
  notebook cells (each API call costs tokens).
- Some topics also ship a **Streamlit app** (`<topic>/<name>_app.py`) as an interactive front
  end for the same analysis. Run one with
  `.venv\Scripts\python.exe -m streamlit run <topic>/<name>_app.py`. To smoke-test that an app
  boots without spending tokens, run it headless (`--server.headless true --server.port <port>`)
  and check `http://localhost:<port>/_stcore/health` returns 200.

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
`vision/_wildlife.py` exports `MODEL`, `PROMPT`, and the image-block builders
`url_image_block(url)`, `image_block(path, media_type)` (local file → base64), and
`bytes_image_block(data, media_type)` (raw bytes, e.g. a Streamlit upload → base64).

Import notes:
- The **notebook** can't rely on `__file__`, so its setup cell adds the module's folder to
  `sys.path` (trying both `.` and the topic folder) before `from _wildlife import ...`, so it
  works whether the working directory is the topic folder or the repo root.
- The **Streamlit app** needs no such guard — Streamlit puts the script's own folder on
  `sys.path`, so a plain `from _wildlife import ...` resolves.

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
