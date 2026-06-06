"""
Document search — Streamlit app.

Drag in a set of documents (PDF, Word, text, markdown, CSV), and search them: Voyage AI embeds
and ranks the chunks for your query, and Claude answers grounded in the top matches — every
claim cited back to the passage it came from. You see both the cited answer and the ranked
passages with their similarity scores.

Run it (Windows / PowerShell, from the repo root):

    .venv\\Scripts\\python.exe -m streamlit run documents/search_app.py

Requires ANTHROPIC_API_KEY and VOYAGE_API_KEY (env vars or a .env file at the repo root).
"""

import os

import streamlit as st
import streamlit.components.v1 as components
from anthropic import Anthropic
from dotenv import load_dotenv

from _documents import (
    EMBED_MODEL,
    MODEL,
    SUPPORTED_EXTS,
    answer,
    build_library,
    render_html,
    retrieve,
)

load_dotenv()


@st.cache_resource
def get_client():
    return Anthropic()


st.set_page_config(page_title="Document search — Claude + Voyage", page_icon="🔎", layout="centered")
st.title("🔎 Search your documents")
st.caption(
    f"Voyage ({EMBED_MODEL}) finds the most relevant passages; Claude ({MODEL}) answers from them "
    "and cites each one. Drop in PDFs, Word docs, text, markdown, or CSV."
)

missing = [k for k in ("ANTHROPIC_API_KEY", "VOYAGE_API_KEY") if not os.environ.get(k)]
if missing:
    st.error(
        f"**Missing {' and '.join(missing)}.** Add to your `.env` (see `.env.example`) or set the "
        "environment variable(s), then reload. Voyage AI powers retrieval; get a key at voyageai.com."
    )
    st.stop()

uploaded = st.file_uploader(
    "Drag in documents",
    type=[ext.lstrip(".") for ext in SUPPORTED_EXTS],
    accept_multiple_files=True,
)

# Embed the library once per file set (re-embedding on every rerun would waste Voyage tokens).
if uploaded:
    signature = tuple((f.name, f.size) for f in uploaded)
    cached = st.session_state.get("library")
    if not cached or cached["signature"] != signature:
        with st.spinner(f"Extracting and embedding {len(uploaded)} document(s) with Voyage…"):
            chunks, skipped = build_library([(f.name, f.getvalue()) for f in uploaded])
        st.session_state["library"] = {"signature": signature, "chunks": chunks, "skipped": skipped}
    lib = st.session_state["library"]
    st.success(
        f"Indexed {len(lib['chunks'])} chunks from {len(uploaded) - len(lib['skipped'])} document(s)."
        + (f" Skipped (no extractable text): {', '.join(lib['skipped'])}." if lib["skipped"] else "")
    )
else:
    st.info("Upload one or more documents to search. Scanned/image-only PDFs have no extractable text.")
    st.session_state.pop("library", None)

col_q, col_k = st.columns([0.78, 0.22])
query = col_q.text_input("Search query", placeholder="e.g. Which animal depends on sea ice?")
top_k = col_k.slider("Passages", min_value=3, max_value=12, value=5)
search = st.button("Search", type="primary", disabled="library" not in st.session_state)

if search:
    chunks = st.session_state["library"]["chunks"]
    if not query.strip():
        st.error("Enter a search query.")
    elif not chunks:
        st.error("No searchable text was extracted from the uploaded documents.")
    else:
        try:
            with st.spinner("Ranking passages and asking Claude…"):
                retrieved = retrieve(query.strip(), chunks, k=top_k)
                content = answer(get_client(), query.strip(), retrieved)
            st.session_state["search_result"] = {
                "query": query.strip(),
                "content": content,
                "retrieved": retrieved,
            }
        except Exception as exc:  # noqa: BLE001 — surface API/network errors to the user
            st.error(f"Search failed: {exc}")

result = st.session_state.get("search_result")
if result:
    components.html(
        render_html(result["query"], result["content"], result["retrieved"]),
        height=760,
        scrolling=True,
    )
