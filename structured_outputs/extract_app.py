"""
Structured outputs — Streamlit extractor.

Paste free-text field notes (one per line); Claude extracts each into a schema-valid sighting
record via `messages.parse`, and the app shows them as a clean table you could write straight to a
database.

Run it (Windows / PowerShell, from the repo root):

    .venv\\Scripts\\python.exe -m streamlit run structured_outputs/extract_app.py

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import os

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from _structured_outputs import MODEL, SAMPLE_NOTES, SightingReport, extract

load_dotenv()


@st.cache_resource
def get_client():
    return Anthropic()


st.set_page_config(page_title="Structured outputs — Claude", page_icon="🧬", layout="centered")
st.title("🧬 Structured extraction")
st.caption(
    f"Claude ({MODEL}) turns messy field notes into schema-valid records via `messages.parse` — "
    "typed, validated, ready for a database. One note per line."
)

with st.sidebar:
    st.subheader("Target schema")
    st.json({n: str(f.annotation) for n, f in SightingReport.model_fields.items()})

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error("**ANTHROPIC_API_KEY is not set.** Add it to `.env` or your environment, then reload.")
    st.stop()

notes_raw = st.text_area("Field notes (one per line)", value="\n".join(SAMPLE_NOTES), height=200)
go = st.button("Extract", type="primary")

if go:
    notes = [n.strip() for n in notes_raw.splitlines() if n.strip()]
    if not notes:
        st.error("Enter at least one field note.")
    else:
        rows, errors = [], []
        progress = st.progress(0.0, text="Extracting…")
        client = get_client()
        for i, note in enumerate(notes):
            try:
                report = extract(client, note)
                row = report.model_dump()
                row["time_of_day"] = report.time_of_day.value
                rows.append(row)
            except Exception as exc:  # noqa: BLE001 — keep going, report per-note failures
                errors.append(f"Note {i + 1}: {exc}")
            progress.progress((i + 1) / len(notes), text=f"Extracted {i + 1}/{len(notes)}")
        progress.empty()
        st.session_state["extract_rows"] = rows
        st.session_state["extract_errors"] = errors

rows = st.session_state.get("extract_rows")
if rows:
    st.divider()
    st.subheader("Extracted records")
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ records.json",
        data=__import__("json").dumps(rows, indent=2),
        file_name="sightings.json",
    )
    for err in st.session_state.get("extract_errors", []):
        st.warning(err)
