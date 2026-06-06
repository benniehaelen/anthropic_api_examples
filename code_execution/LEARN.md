# Learn — Code execution (server tool)

A study sheet for the `code_execution/` example. Pair it with the notebook
([`code_execution.ipynb`](code_execution.ipynb)), the Streamlit app
([`code_app.py`](code_app.py)), and the CLI ([`run_code.py`](run_code.py)).

**Where this fits in the CCA exam:** primarily **Agentic Architecture** (27%) — code execution is
a core agent primitive — with strong ties to **Tool Design & MCP Integration** (18%, server vs.
client tools) and **Context & Reliability** (15%, `pause_turn`). See the
[STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

- Explain how a **server tool** differs from a client-defined tool (no tool-result loop you write).
- Attach data with the **Files API** + `container_upload` and retrieve files Claude creates.
- Handle long jobs with **`pause_turn`** and reuse a sandbox via **`container`**.
- Recall the sandbox constraints and the pricing model.

## Key concepts

- **Server tool = Anthropic runs the code.** You declare
  `{"type": "code_execution_20250825", "name": "code_execution"}`; the response already contains
  the code Claude ran (`server_tool_use`) and its output (`*_tool_result`). There is **no
  client-side `tool_use` → `tool_result` round-trip** for you to implement — unlike a custom tool
  you define and execute yourself.
- **Two sub-tools appear automatically:** `bash_code_execution` (run commands) and
  `text_editor_code_execution` (view/create/edit files).
- **Files in:** upload via the Files API (beta header `files-api-2025-04-14`), then reference with
  a `{"type": "container_upload", "file_id": ...}` block.
- **Files out:** files Claude creates surface as `file_id`s inside the result blocks; download them
  with `client.beta.files.download(...)`.
- **`pause_turn`:** long turns may stop with `stop_reason == "pause_turn"`. Resume by sending the
  partial response back unchanged (see `run_until_done`).
- **Stateful sessions:** pass `container=<previous response>.container.id` to reuse the same
  sandbox and keep files across requests.
- **Sandbox:** Python 3.11, ~5 GiB RAM, **no internet**, with pandas/numpy/matplotlib/scikit-learn
  preinstalled.
- **Tool versions:** `code_execution_20250825` (Bash + files, all current models) vs
  `code_execution_20260120` (adds persistent REPL state + programmatic tool calling; Opus 4.5+ /
  Sonnet 4.5+).

## API cheat-sheet

```python
TOOL = {"type": "code_execution_20250825", "name": "code_execution"}

f = client.beta.files.upload(file=open("data.csv", "rb"))   # Files API
resp = client.beta.messages.create(
    model="claude-sonnet-4-5", max_tokens=4096, betas=["files-api-2025-04-14"], tools=[TOOL],
    messages=[{"role": "user", "content": [
        {"type": "text", "text": "Clean this CSV and chart it as chart.png."},
        {"type": "container_upload", "file_id": f.id}]}])
# if resp.stop_reason == "pause_turn": resubmit with the response appended (run_until_done)
```

## Common pitfalls

- **Writing a tool-result loop.** It's a *server* tool — don't try to execute and return results;
  they come back in the response.
- **Ignoring `pause_turn`.** Treating a paused turn as "done" truncates long jobs. Always resume.
- **Expecting internet.** The sandbox has none — upload or generate everything it needs in-container.
- **Forgetting to download.** Files Claude creates live in the sandbox; you must pull them via the
  Files API before the container goes away.
- **Billing surprises.** Code execution is **free when `web_search`/`web_fetch` is in the same
  request**; otherwise it's billed by execution time (5-min minimum), and **attaching files
  preloads the container, so time is billed even if Claude never runs code**.
- **Tool/model mismatch.** Use the tool version that matches your model (e.g. `20260120` needs
  Opus 4.5+/Sonnet 4.5+).

## Try it yourself

1. **Warm-up:** ask for a computed answer ("std dev of the first 50 primes, run code") and watch
   the `server_tool_use` + result blocks come back without any loop.
2. **Your data:** upload your own CSV in the app and ask for a profile + a chart; download the PNG.
3. **Stateful:** make one request that writes a file, then a second with
   `container=<first>.container.id` that reads it back — confirm state persists.
4. **Force a chart:** ask for a specific filename and confirm it appears via `extract_file_ids`.

## Check yourself

1. **What's the key difference between the code execution tool and a custom (client) tool?**
   <details><summary>Answer</summary>Code execution is a *server* tool — Anthropic runs the code
   and returns results inline, so there's no client-side `tool_use`→`tool_result` loop. A custom
   tool is executed by *you* and the result returned to the API.</details>

2. **The response comes back with `stop_reason == "pause_turn"`. What do you do?**
   <details><summary>Answer</summary>Resume: append the partial response to your messages and call
   again, repeating until the stop reason is a real finish (e.g. `end_turn`).</details>

3. **How do you get a file Claude created in the sandbox?**
   <details><summary>Answer</summary>Its `file_id` appears in the execution result blocks; download
   it via the Files API (`client.beta.files.download(file_id)`).</details>

4. **When is code execution free, and what's a sneaky way to get billed for it?**
   <details><summary>Answer</summary>Free when `web_search` or `web_fetch` is in the same request.
   Otherwise it's billed by execution time — and attaching a file preloads the container, so you're
   billed even if Claude never runs any code.</details>

## Further reading

- [Code execution tool — Claude API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)
- [Files API](https://platform.claude.com/docs/en/build-with-claude/files)
