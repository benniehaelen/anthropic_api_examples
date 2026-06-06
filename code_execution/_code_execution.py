"""
Shared building blocks for the code-execution example.

The **code execution** tool lets Claude write and run Python/Bash and edit files inside a secure
sandbox on Anthropic's servers. It is a *server tool*: Anthropic runs the code and returns the
results, so there is no client-side tool-result loop to write — you send a request, and the
response already contains the code Claude ran and its output.

This module centralizes the tool definition, a request helper that handles long runs, a parser
that turns the interleaved response blocks into simple events for printing or rendering, the
Files-API upload/download helpers, and a generator for the messy sample CSV. Imported by
`code_execution.ipynb`, `code_app.py`, and `run_code.py`.

Sandbox facts: Python 3.11 on Linux, ~5 GiB RAM, no internet, with pandas/numpy/matplotlib/
scikit-learn preinstalled.
"""

import os

# The reference notebook uses Sonnet 4.5; code execution works on every current model. Switch to
# claude-opus-4-8 for stronger code generation (the citations/documents topics use Opus).
MODEL = "claude-sonnet-4-5"

# code_execution_20250825: Bash + file ops, available on every current model. (20260120 adds
# persistent REPL state + programmatic tool calling on Opus 4.5+/Sonnet 4.5+.)
CODE_EXECUTION_TOOL = {"type": "code_execution_20250825", "name": "code_execution"}
FILES_BETA = "files-api-2025-04-14"


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
def run_until_done(create, *, messages, **kwargs):
    """Resubmit on `pause_turn` until Claude finishes the turn.

    Long-running jobs may return `stop_reason == "pause_turn"`; the fix is to feed the partial
    response back unchanged and let Claude continue.
    """
    while True:
        response = create(messages=messages, **kwargs)
        if response.stop_reason == "pause_turn":
            messages = messages + [{"role": "assistant", "content": response.content}]
            continue
        return response


def run_analysis(client, prompt, file_id=None, max_tokens=4096, container=None):
    """Send a code-execution request, optionally with an uploaded file, handling `pause_turn`.

    Pass `container=<previous response>.container.id` to reuse a sandbox across requests.
    """
    content = [{"type": "text", "text": prompt}]
    if file_id:
        content.append({"type": "container_upload", "file_id": file_id})
    kwargs = dict(
        model=MODEL,
        betas=[FILES_BETA],
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
        tools=[CODE_EXECUTION_TOOL],
    )
    if container:
        kwargs["container"] = container
    return run_until_done(client.beta.messages.create, **kwargs)


# --------------------------------------------------------------------------- #
# Response parsing
# --------------------------------------------------------------------------- #
def parse_events(response):
    """Turn the interleaved response blocks into simple dicts for printing or rendering.

    A code-execution response is a sequence of: assistant `text`, `server_tool_use` (the code or
    command Claude ran), and `*_tool_result` blocks carrying stdout/stderr/return codes.
    """
    events = []
    for block in response.content:
        btype = block.type
        if btype == "text":
            events.append({"kind": "text", "text": block.text})
        elif btype == "server_tool_use":
            events.append({"kind": "ran", "name": block.name, "input": block.input or {}})
        elif btype == "bash_code_execution_tool_result":
            content = block.content
            events.append({
                "kind": "bash_result",
                "stdout": getattr(content, "stdout", "") or "",
                "stderr": getattr(content, "stderr", "") or "",
                "return_code": getattr(content, "return_code", None),
            })
        elif btype == "text_editor_code_execution_tool_result":
            content = block.content
            events.append({"kind": "file_op", "op": getattr(content, "type", "")})
        else:
            events.append({"kind": btype})
    return events


def show_response(response):
    """Pretty-print a code-execution response (for notebooks / CLIs)."""
    for event in parse_events(response):
        kind = event["kind"]
        if kind == "text":
            print("\n── assistant ──\n" + event["text"])
        elif kind == "ran":
            print(f"\n── ran ({event['name']}) ──")
            print(event["input"])
        elif kind == "bash_result":
            print(f"\n── bash result (return_code={event['return_code']}) ──")
            if event["stdout"]:
                print(event["stdout"])
            if event["stderr"]:
                print("stderr:\n" + event["stderr"])
        elif kind == "file_op":
            print(f"\n── file op ({event['op']}) ──")
        else:
            print(f"\n── {kind} ──")


def assistant_text(response):
    """Concatenate just the assistant's narrative text blocks."""
    return "\n".join(b.text for b in response.content if b.type == "text")


# --------------------------------------------------------------------------- #
# Files API
# --------------------------------------------------------------------------- #
def upload_file(client, path):
    """Upload a local file through the Files API; returns the file object (use `.id`)."""
    with open(path, "rb") as handle:
        return client.beta.files.upload(file=handle)


def extract_file_ids(response):
    """Collect file ids from any execution result block that produced files."""
    file_ids = []
    for item in response.content:
        result = getattr(item, "content", None)
        produced = getattr(result, "content", None)
        if isinstance(produced, list):
            for f in produced:
                fid = getattr(f, "file_id", None)
                if fid:
                    file_ids.append(fid)
    return file_ids


def download_created_files(client, response, dest_dir="."):
    """Download every file Claude created in the sandbox; returns the saved paths."""
    saved = []
    for file_id in extract_file_ids(response):
        meta = client.beta.files.retrieve_metadata(file_id)
        data = client.beta.files.download(file_id)
        path = os.path.join(dest_dir, meta.filename)
        data.write_to_file(path)
        saved.append(path)
    return saved


# --------------------------------------------------------------------------- #
# Sample data
# --------------------------------------------------------------------------- #
# A deliberately messy sales CSV: inconsistent region capitalization, missing units_sold, missing
# revenue (recomputable), an exact duplicate row, and stray whitespace in a product name.
SAMPLE_SALES_CSV = """date,region,product,units_sold,unit_price,revenue
2024-01-03,North,Widget,120,9.99,1198.80
2024-01-04,north,Widget,90,9.99,
2024-01-05,SOUTH,Gadget,60,19.50,1170.00
2024-01-06,South,Gadget,,19.50,
2024-01-07,East,Gizmo,45,29.00,1305.00
2024-01-08,east, Gizmo ,45,29.00,1305.00
2024-01-09,West,Widget,200,9.99,1998.00
2024-01-10,west,Gadget,30,19.50,585.00
2024-01-11,North,Gizmo,75,29.00,
2024-01-12,North,Gizmo,75,29.00,2175.00
2024-01-12,North,Gizmo,75,29.00,2175.00
2024-01-13,South,Widget,,9.99,
2024-01-14,East,Gadget,110,19.50,2145.00
2024-01-15,WEST,Widget,160,9.99,1598.40
2024-01-16,north,Gadget,40,19.50,780.00
2024-01-17,South,Gizmo,55,29.00,1595.00
2024-01-18,East,Widget,95,9.99,949.05
2024-01-19,west,Gizmo,65,29.00,
2024-01-20,North,Gadget,85,19.50,1657.50
"""


def write_sample_csv(path="sample_sales.csv"):
    """Write the messy sample sales CSV to disk; returns the path."""
    with open(path, "w", newline="") as handle:
        handle.write(SAMPLE_SALES_CSV)
    return path
