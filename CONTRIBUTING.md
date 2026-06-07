# Contributing

Thanks for adding to this collection. The repo's value is that **every example runs and stays
consistent**, so new topics should follow the established shape. (`CLAUDE.md` documents the same
conventions for AI assistants.)

## Setup

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env   # then add ANTHROPIC_API_KEY (and VOYAGE_API_KEY for the documents topic)
```

Run the offline smoke test any time — it needs no API key:

```powershell
.venv\Scripts\python.exe tests/smoke_test.py
```

## Repository shape

Each capability is a **top-level topic folder** (e.g. `vision/`, `tool_use/`). Helpers stay
**flat inside the topic** — no `helpers/` sub-folders (it keeps notebook imports trivial). A topic
typically contains:

| File | Purpose |
| --- | --- |
| `_<topic>.py` | Shared module: a `MODEL` constant, the reusable helpers, and any generated sample data. The single source of truth the notebook/app/CLI all import. |
| `<name>.ipynb` | A guided, top-to-bottom walkthrough. |
| `<name>_app.py` | *(optional)* A Streamlit app. |
| `run_*.py` | *(optional)* A CLI runner. |
| `LEARN.md` | A study sheet (see structure below). |

## Adding a topic — checklist

1. **Create `<topic>/_<topic>.py`** with a `MODEL` constant, the helpers, and a sample-data
   generator if the example needs input. Keep it self-contained (import heavy/optional deps like
   `cv2`, `voyageai`, `mcp` *inside* functions so the module imports cheaply).
2. **Write the notebook.** Start with a markdown title cell (capability + `ANTHROPIC_API_KEY`
   note). The setup cell must import from the shared module using the path-guard so it works
   whether the working directory is the repo root or the topic folder:

   ```python
   import os, sys
   for _p in (".", "<topic>"):
       if os.path.isfile(os.path.join(_p, "_<topic>.py")) and _p not in sys.path:
           sys.path.insert(0, _p)
   from _<topic> import ...
   ```

   (Streamlit apps and CLIs don't need the guard — the script's folder is already on `sys.path`.)
3. **Add a `<name>_app.py` and/or `run_*.py`** if they add value, importing the same module.
4. **Write `LEARN.md`** (next section).
5. **Wire it up:** add a section + `📚 Study sheet` link in `README.md`; add a row to the
   domain-coverage table and the suggested-order list in `STUDY_GUIDE.md`; add the topic to the
   list (and a short note) in `CLAUDE.md`. Add any new dependency to `requirements.txt` and any
   generated artifact to `.gitignore`.
6. **Verify** (see below), then open a PR. CI must be green.

## LEARN.md structure

Follow the existing sheets so studying stays consistent. Sections, in order:

1. Where it fits in the CCA exam (domain + weight) → link `../STUDY_GUIDE.md`
2. Learning objectives
3. Key concepts
4. API cheat-sheet (copy-pasteable)
5. Common pitfalls
6. Try it yourself (exercises tied to the code)
7. Check yourself (Q&A with collapsible `<details>` answers)
8. Further reading (official docs)

## Conventions

- **Model.** Most topics use `claude-sonnet-4-5`; the citation-quality-sensitive topics
  (`citations/`, `documents/`) and `agents/` use `claude-opus-4-8`. Pick one and note the choice
  in a comment. Use exact model-ID strings (no date suffixes).
- **Keys.** Load from `.env` via `python-dotenv`. **Never commit `.env` or a real key** — only
  `.env.example` (empty placeholders) is tracked. Don't paste keys into issues/PRs/chats.
- **Self-contained & runnable.** Prefer generated sample data or public, license-clear URLs over
  committing binaries. Gitignore anything a run writes.
- **Cost honesty.** Note when a notebook/app spends tokens; keep loops and sampling bounded.
- **Match the surroundings.** Mirror the existing comment density, naming, and docstring style.

## Verifying before a PR

- `python tests/smoke_test.py` passes (compile + import + notebook validation; CI runs this).
- New `.py` files compile; the notebook is valid (the smoke test checks JSON shape).
- If you added a Streamlit app, it boots headless:
  `python -m streamlit run <topic>/<name>_app.py --server.headless true --server.port 8600`,
  then `http://localhost:8600/_stcore/health` returns `200`.
- Optionally exercise one real run end-to-end (this costs tokens) and sanity-check the output.
