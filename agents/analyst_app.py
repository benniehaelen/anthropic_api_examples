"""
Self-correcting analyst — Streamlit app.

Give it a CSV and a question. An orchestrator decomposes the question, analyst agents write and run
code to answer each part, a critic reviews each finding (and sends it back for revision if it's
weak), and a synthesizer writes the final report. You watch the whole multi-agent loop live.

Run it (Windows / PowerShell, from the repo root):

    .venv\\Scripts\\python.exe -m streamlit run agents/analyst_app.py

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import os
import tempfile

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from _analyst import (
    DEFAULT_QUESTION,
    MODEL,
    OBSERVATIONS_CSV,
    orchestrate,
    upload_dataset,
    write_dataset,
)

load_dotenv()


@st.cache_resource
def get_client():
    return Anthropic()


st.set_page_config(page_title="Analyst agent — Claude", page_icon="🧠", layout="centered")
st.title("🧠 Self-correcting analyst")
st.caption(
    f"A multi-agent loop ({MODEL}): orchestrator → analyst (runs code) ⇄ critic (reviews & sends "
    "back) → synthesizer. Give it data and a question; watch it work."
)

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error("**ANTHROPIC_API_KEY is not set.** Add it to `.env` or your environment, then reload.")
    st.stop()

use_sample = st.toggle("Use the built-in wildlife-survey dataset (with planted data issues)", value=True)
uploaded = None
if not use_sample:
    uploaded = st.file_uploader("Upload a CSV", type=["csv"])

question = st.text_area("Question", value=DEFAULT_QUESTION, height=80)
c1, c2 = st.columns(2)
max_subtasks = c1.slider("Max sub-analyses", 2, 4, 3)
max_revisions = c2.slider("Max revisions per sub-analysis", 0, 2, 1)
run = st.button("Run analysis", type="primary")


def render_event(event):
    k = event["kind"]
    if k == "plan":
        st.markdown("🧭 **Orchestrator — plan**")
        for i, s in enumerate(event["subtasks"], 1):
            st.markdown(f"&nbsp;&nbsp;{i}. {s}")
    elif k == "subtask_start":
        st.markdown(f"---\n**🔎 Sub-analysis:** {event['subtask']}")
    elif k == "analyst":
        st.markdown(f"🔬 **Analyst** (attempt {event['attempt']})")
        if event["stdout"]:
            with st.expander("computed output"):
                st.code(event["stdout"], language="text")
        st.markdown(event["finding"])
    elif k == "critic":
        if event["passed"]:
            st.success(f"✅ Critic: passed (attempt {event['attempt']})")
        else:
            st.warning(f"♻️ Critic: revise — {'; '.join(event['issues'])}")
    elif k == "synthesizing":
        st.markdown("🧩 **Synthesizer** — combining verified findings…")


if run:
    if not question.strip():
        st.error("Enter a question.")
    elif not use_sample and uploaded is None:
        st.error("Upload a CSV or switch on the built-in dataset.")
    else:
        client = get_client()
        if use_sample:
            path = write_dataset(os.path.join(tempfile.gettempdir(), "observations.csv"))
            csv_text = OBSERVATIONS_CSV
        else:
            path = os.path.join(tempfile.gettempdir(), uploaded.name)
            with open(path, "wb") as h:
                h.write(uploaded.getvalue())
            csv_text = uploaded.getvalue().decode("utf-8", errors="replace")
        try:
            with st.status("Running multi-agent analysis…", expanded=True) as status:
                file_id = upload_dataset(client, path).id
                out = orchestrate(client, question.strip(), file_id, csv_text,
                                  max_subtasks=max_subtasks, max_revisions=max_revisions,
                                  emit=render_event)
                status.update(label="Analysis complete", state="complete")
            st.session_state["analyst_final"] = out["final"]
        except Exception as exc:  # noqa: BLE001 — surface API/network errors to the user
            st.error(f"Run failed: {exc}")

if st.session_state.get("analyst_final"):
    st.divider()
    st.subheader("Final report")
    st.markdown(st.session_state["analyst_final"])
