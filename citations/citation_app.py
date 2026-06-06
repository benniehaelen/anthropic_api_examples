"""
Citations — Streamlit app.

Provide source documents, ask a question, and Claude answers *grounded in the documents*:
the answer renders as an editorial page where every claim Claude drew from a source gets a red
footnote marker. Hover a marker to preview the exact cited text; click it to jump to the
reference and highlight it — the same behavior as a hand-built footnoted article, but every
citation is produced by the Claude Citations API.

Run it (Windows / PowerShell, from the repo root):

    .venv\\Scripts\\python.exe -m streamlit run citations/citation_app.py

Requires ANTHROPIC_API_KEY in your environment or a .env file at the repo root.
"""

import os

import streamlit as st
import streamlit.components.v1 as components
from anthropic import Anthropic
from dotenv import load_dotenv

from _citations import (
    DEFAULT_QUESTION,
    MODEL,
    WILDLIFE_DOCS,
    ask,
    location_label,
    render_html,
    text_blocks,
)

load_dotenv()


@st.cache_resource
def get_client():
    return Anthropic()


def docs_to_text(docs):
    """Format the sample docs into the editable '# Title / body' text-area format."""
    return "\n\n".join(f"# {d['title']}\n{d['text']}" for d in docs)


def parse_docs(raw):
    """Parse the '# Title' + body text-area format back into [{title, text}]."""
    docs, title, buffer = [], None, []
    for line in raw.splitlines():
        if line.startswith("# "):
            if title is not None:
                docs.append({"title": title, "text": "\n".join(buffer).strip()})
            title, buffer = line[2:].strip(), []
        else:
            buffer.append(line)
    if title is not None:
        docs.append({"title": title, "text": "\n".join(buffer).strip()})
    return [d for d in docs if d["text"]]


st.set_page_config(page_title="Citations — Claude", page_icon="📑", layout="centered")
st.title("📑 Grounded answers with citations")
st.caption(
    "Claude answers from the documents you provide and cites the exact source text for each "
    f"claim. Hover a footnote to preview its source, click to jump to it. Model: {MODEL}."
)

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(
        "**ANTHROPIC_API_KEY is not set.** Copy `.env.example` to `.env` and add your key, "
        "or set the environment variable, then reload."
    )
    st.stop()

with st.expander("Source documents (edit freely — start each doc with `# Title`)", expanded=False):
    docs_raw = st.text_area(
        "documents",
        value=docs_to_text(WILDLIFE_DOCS),
        height=260,
        label_visibility="collapsed",
    )

question = st.text_input("Question", value=DEFAULT_QUESTION)
ask_clicked = st.button("Ask", type="primary")

if ask_clicked:
    docs = parse_docs(docs_raw)
    if not docs:
        st.error("Add at least one document (a `# Title` line followed by some text).")
    elif not question.strip():
        st.error("Enter a question.")
    else:
        with st.spinner("Asking Claude with citations enabled…"):
            try:
                content = ask(get_client(), docs, question.strip())
                st.session_state["cite_result"] = {"question": question.strip(), "content": content}
            except Exception as exc:  # noqa: BLE001 — surface API/network errors to the user
                st.error(f"Request failed: {exc}")

result = st.session_state.get("cite_result")
if result:
    components.html(render_html(result["question"], result["content"]), height=720, scrolling=True)

    # Show the raw citation data behind the rendering — the point of the demo.
    blocks = text_blocks(result["content"])
    raw = [
        {
            "claim": b["text"],
            "citations": [
                {
                    "document_title": c.get("document_title"),
                    "location": location_label(c),
                    "cited_text": c.get("cited_text"),
                }
                for c in b["citations"]
            ],
        }
        for b in blocks
        if b["citations"]
    ]
    with st.expander(f"Raw citations from the API ({sum(len(b['citations']) for b in blocks)} total)"):
        st.json(raw)
