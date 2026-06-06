"""
Prompt caching — Streamlit "cache lab".

Run a batch of questions against a large cached prefix and watch the savings appear: the first
request writes the cache, the rest read it. Toggle caching off to see the difference, or inject a
volatile prefix to watch the cache silently miss.

Run it (Windows / PowerShell, from the repo root):

    .venv\\Scripts\\python.exe -m streamlit run prompt_caching/cache_app.py

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import os

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from _prompt_caching import (
    MODEL,
    QUESTIONS,
    ask,
    prefix_token_count,
    relative_input_cost,
    usage_of,
)

load_dotenv()


@st.cache_resource
def get_client():
    return Anthropic()


@st.cache_data(show_spinner=False)
def cached_prefix_tokens():
    return prefix_token_count(get_client())


st.set_page_config(page_title="Prompt caching — Claude", page_icon="⚡", layout="centered")
st.title("⚡ Prompt caching lab")
st.caption(
    f"Reuse a large cached prefix across requests and measure it. Model: {MODEL}. The cache write "
    "happens on the first request; later requests read it at ~0.1x input price."
)

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error("**ANTHROPIC_API_KEY is not set.** Add it to `.env` or your environment, then reload.")
    st.stop()

st.metric("Cacheable prefix size", f"{cached_prefix_tokens():,} tokens",
          help="Must exceed the model minimum (1024 on Sonnet 4.5, 4096 on Opus 4.8) to cache.")

n = st.slider("How many questions to run", 1, len(QUESTIONS), 4)
col1, col2 = st.columns(2)
use_cache = col1.toggle("Enable caching", value=True)
volatile = col2.toggle("Inject volatile prefix (break the cache)", value=False,
                       help="Prepends a changing timestamp before the breakpoint — the classic "
                            "silent invalidator. Every request misses and re-writes.")
run = st.button("Run", type="primary")

if run:
    client = get_client()
    rows = []
    progress = st.progress(0.0, text="Running…")
    try:
        for i, q in enumerate(QUESTIONS[:n]):
            vp = f"Request time: 2026-06-06T12:00:{i:02d}Z" if volatile else None
            resp, secs = ask(client, q, cache=use_cache, volatile_prefix=vp)
            u = usage_of(resp)
            rows.append({
                "question": q,
                "input (full)": u["input"],
                "cache_write": u["cache_write"],
                "cache_read": u["cache_read"],
                "output": u["output"],
                "latency_s": round(secs, 2),
                "rel_input_cost": round(relative_input_cost(u), 2),
            })
            progress.progress((i + 1) / n, text=f"Ran {i + 1}/{n}")
        st.session_state["cache_rows"] = rows
    except Exception as exc:  # noqa: BLE001 — surface API/network errors to the user
        st.error(f"Run failed: {exc}")
    finally:
        progress.empty()

rows = st.session_state.get("cache_rows")
if rows:
    total_read = sum(r["cache_read"] for r in rows)
    total_write = sum(r["cache_write"] for r in rows)
    total_full = sum(r["input (full)"] for r in rows)
    avg_relcost = sum(r["rel_input_cost"] for r in rows) / len(rows)

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tokens read from cache", f"{total_read:,}")
    m2.metric("Tokens written", f"{total_write:,}")
    m3.metric("Full-price input", f"{total_full:,}")
    m4.metric("Avg input cost vs uncached", f"{avg_relcost:.0%}",
              help="Lower is better; ~10% means the prefix was almost entirely served from cache.")

    st.subheader("Per-request token breakdown")
    st.bar_chart(
        {
            "cache_read": [r["cache_read"] for r in rows],
            "cache_write": [r["cache_write"] for r in rows],
            "input (full)": [r["input (full)"] for r in rows],
        }
    )

    st.subheader("Details")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if total_read == 0:
        st.info(
            "No cache reads. That's expected if caching is off, the volatile-prefix toggle is on, "
            "or you ran a single request (the first call only writes)."
        )
