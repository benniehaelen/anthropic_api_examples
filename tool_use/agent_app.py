"""
Tool use — Streamlit agent.

Ask a question; Claude decides which custom tools to call, the app runs them, and you watch the
agentic loop unfold: each tool call, its result, and the final grounded answer.

Run it (Windows / PowerShell, from the repo root):

    .venv\\Scripts\\python.exe -m streamlit run tool_use/agent_app.py

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import os

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from _tool_use import MODEL, TOOLS, run_loop

load_dotenv()


@st.cache_resource
def get_client():
    return Anthropic()


st.set_page_config(page_title="Tool use — Claude", page_icon="🛠️", layout="centered")
st.title("🛠️ Tool-use agent")
st.caption(
    f"Claude ({MODEL}) calls custom tools you implement, in a loop, to answer your question. "
    "You run the tools; Claude decides when."
)

with st.sidebar:
    st.subheader("Available tools")
    for tool in TOOLS:
        st.markdown(f"**`{tool['name']}`** — {tool['description']}")
    st.caption("Try: \"Weather in Paris, and 18°C in Fahrenheit?\"")

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error("**ANTHROPIC_API_KEY is not set.** Add it to `.env` or your environment, then reload.")
    st.stop()

question = st.text_input("Ask a question", value="What's the weather in Paris, and what is 18°C in Fahrenheit?")
go = st.button("Run", type="primary")

if go:
    if not question.strip():
        st.error("Enter a question.")
    else:
        try:
            with st.spinner("Claude is working (and calling tools)…"):
                final, transcript = run_loop(get_client(), question.strip())
            st.session_state["agent_result"] = {"final": final, "transcript": transcript}
        except Exception as exc:  # noqa: BLE001 — surface API/network errors to the user
            st.error(f"Run failed: {exc}")

result = st.session_state.get("agent_result")
if result:
    st.divider()
    st.subheader("Agent transcript")
    for e in result["transcript"]:
        if e["kind"] == "text":
            if e["text"].strip():
                st.markdown(e["text"])
        elif e["kind"] == "tool_call":
            st.markdown(f"🛠️ **calls `{e['name']}`**")
            st.code(", ".join(f"{k}={v!r}" for k, v in e["input"].items()), language="text")
        elif e["kind"] == "tool_result":
            label = "⚠️ tool error" if e["is_error"] else "✅ tool result"
            st.code(f"{label}: {e['content']}", language="text")

    st.divider()
    st.subheader("Answer")
    st.markdown(result["final"] or "_(no final text)_")
