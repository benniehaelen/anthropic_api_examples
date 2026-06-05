# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of **self-contained Anthropic API examples**, each demonstrating one capability of
the Claude Messages API. Examples are Jupyter notebooks organized **by topic** under
`examples/<topic>/`, one folder per capability (e.g. `vision/`, and future siblings like
`tool-use/`, `prompt-caching/`, `extended-thinking/`). Every example lives under a topic folder
— there are no loose notebooks directly in `examples/`. The first example is
`examples/vision/wildlife_id.ipynb` (image analysis).

## Environment & commands

- **Python 3.14** via the local venv at `.venv/`. Platform is **Windows / PowerShell** — invoke
  the venv interpreter directly to avoid activation-state issues:
  - Install deps: `.venv\Scripts\python.exe -m pip install -r requirements.txt`
  - Run a script: `.venv\Scripts\python.exe <script.py>`
- The **API key** is read from a `.env` file at the repo root (`ANTHROPIC_API_KEY`) via
  `python-dotenv`; `.env.example` is the template. `.env` is gitignored.
- There is **no test suite or linter** configured yet. Examples are validated by running the
  notebook cells (each API call costs tokens).

## The shared example pattern

Every notebook is expected to be self-contained but follows the same shape established by
`wildlife_id.ipynb`. When adding or editing examples, reuse this convention rather than
inventing a new one:

- **Setup cell**: `load_dotenv()`, then `client = Anthropic()` and a `model` string
  (currently `claude-sonnet-4-5`).
- **Helper cell**: small wrappers reused across examples — `add_user_message` /
  `add_assistant_message` (which accept either a raw value or an SDK `Message` and unwrap
  `.content`), `chat(messages, system=, temperature=, tools=, thinking=, ...)` that builds the
  `client.messages.create(**params)` call, `text_from_message` to concatenate text blocks, and
  `url_image_block` / `image_block` to build image content blocks from a URL or a local file.
- The example-specific prompt and the API call come last, printing `text_from_message(response)`.

## Conventions for new examples

- Place each example at `examples/<topic>/<name>.ipynb` (no numeric prefix). Reuse an existing
  topic folder when one fits; otherwise create a new topic folder named after the capability.
  Add a row under the matching topic heading in `README.md` (create the heading if new).
- Keep examples runnable with no local assets when possible — prefer public **image URLs**
  (e.g. public-domain NPS/government photos) over committing binary files, and document the
  source and license in a markdown cell.
- Start each notebook with a markdown title cell describing the capability and noting the
  `ANTHROPIC_API_KEY` requirement.
