"""
Code execution — Streamlit analysis sandbox.

Upload a data file (or use the built-in messy sample), describe what you want, and Claude writes
and runs code in Anthropic's sandbox to do it — then this app shows the assistant's narrative,
the code/commands it ran, the output, and any files it produced (charts inline, everything else
as a download).

Run it (Windows / PowerShell, from the repo root):

    .venv\\Scripts\\python.exe -m streamlit run code_execution/code_app.py

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import os
import tempfile

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from _code_execution import (
    MODEL,
    download_created_files,
    extract_file_ids,
    parse_events,
    run_analysis,
    upload_file,
    write_sample_csv,
)

load_dotenv()


@st.cache_resource
def get_client():
    return Anthropic()


DEFAULT_PROMPT = (
    "Load this CSV and tell me what data-quality problems you find. Then clean it (title-case the "
    "regions, trim product names, drop exact duplicate rows, fill missing revenue as "
    "units_sold * unit_price), show total revenue by region, and save a clean bar chart of "
    "revenue by region as revenue_by_region.png. Explain what you did."
)

st.set_page_config(page_title="Code execution — Claude", page_icon="🧮", layout="centered")
st.title("🧮 Code execution sandbox")
st.caption(
    f"Claude ({MODEL}) writes and runs Python/Bash in Anthropic's sandbox to analyze your data — "
    "no local execution. Upload a file, or try the built-in messy sales CSV."
)

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(
        "**ANTHROPIC_API_KEY is not set.** Copy `.env.example` to `.env` and add your key, "
        "or set the environment variable, then reload."
    )
    st.stop()

use_sample = st.toggle("Use the built-in messy sales CSV", value=True)
uploaded = None
if not use_sample:
    uploaded = st.file_uploader("Upload a data file (CSV, JSON, TXT, Excel, …)")

prompt = st.text_area("What should Claude do?", value=DEFAULT_PROMPT, height=130)
run = st.button("Run", type="primary")


def render_events(events):
    """Render the interleaved transcript: narrative, code/commands, and output."""
    for event in events:
        kind = event["kind"]
        if kind == "text":
            if event["text"].strip():
                st.markdown(event["text"])
        elif kind == "ran":
            name, data = event["name"], event["input"]
            if name == "text_editor_code_execution":
                label = f"📝 {data.get('command', 'edit')} `{data.get('path', '')}`"
                if data.get("file_text"):
                    st.markdown(label)
                    st.code(data["file_text"], language="python")
                else:
                    st.markdown(label)
            else:  # bash_code_execution
                st.markdown("⚙️ **ran**")
                st.code(data.get("command", ""), language="bash")
        elif kind == "bash_result":
            if event["stdout"]:
                st.code(event["stdout"], language="text")
            if event["stderr"]:
                with st.expander("stderr"):
                    st.code(event["stderr"], language="text")
            if event["return_code"] not in (None, 0):
                st.warning(f"return code {event['return_code']}")
        elif kind == "file_op":
            st.caption(f"file op · {event['op']}")


if run:
    if not prompt.strip():
        st.error("Tell Claude what to do.")
    else:
        client = get_client()
        try:
            with st.spinner("Uploading data…"):
                if use_sample:
                    tmp = os.path.join(tempfile.gettempdir(), "sample_sales.csv")
                    write_sample_csv(tmp)
                    file_id = upload_file(client, tmp).id
                elif uploaded is not None:
                    tmp = os.path.join(tempfile.gettempdir(), uploaded.name)
                    with open(tmp, "wb") as handle:
                        handle.write(uploaded.getvalue())
                    file_id = upload_file(client, tmp).id
                else:
                    file_id = None
            with st.spinner("Claude is writing and running code in the sandbox…"):
                response = run_analysis(client, prompt.strip(), file_id=file_id)
                out_dir = tempfile.mkdtemp()
                saved = download_created_files(client, response, dest_dir=out_dir)
            st.session_state["code_result"] = {
                "events": parse_events(response),
                "saved": saved,
            }
        except Exception as exc:  # noqa: BLE001 — surface API/network errors to the user
            st.error(f"Run failed: {exc}")

result = st.session_state.get("code_result")
if result:
    st.divider()
    render_events(result["events"])

    if result["saved"]:
        st.divider()
        st.subheader("Files Claude created")
        for path in result["saved"]:
            name = os.path.basename(path)
            with open(path, "rb") as handle:
                data = handle.read()
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                st.image(data, caption=name, use_container_width=True)
            else:
                st.download_button(f"⬇️ {name}", data=data, file_name=name)
