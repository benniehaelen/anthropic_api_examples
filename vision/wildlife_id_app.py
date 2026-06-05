"""
Wildlife identification — Streamlit app.

A polished front end for the same analysis as `wildlife_id.ipynb`: paste a public image
URL or drag in a photo, and Claude's vision capability returns a structured identification
(subject detection, species ID, look-alikes, habitat cues) plus a 1-4 confidence rating.

It also reports location two ways: precise GPS coordinates read from the photo's EXIF
metadata when present, and Claude's region-level estimate inferred from the image regardless.

Run it (Windows / PowerShell, from the repo root):

    .venv\\Scripts\\python.exe -m streamlit run vision/wildlife_id_app.py

Requires ANTHROPIC_API_KEY in your environment or a .env file at the repo root.
"""

import os
import re

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

# Shared building blocks (model, prompt, image helpers) live in _wildlife.py, kept in sync
# with the notebook. Streamlit puts this script's folder on sys.path, so a plain import works.
from _wildlife import (
    MODEL,
    PROMPT,
    bytes_image_block,
    extract_gps,
    fetch_image_bytes,
    url_image_block,
)

load_dotenv()

MAX_TOKENS = 4000
SUPPORTED_TYPES = ["jpg", "jpeg", "png", "gif", "webp"]

# label, dot color, soft background — keyed by the 1-4 rating
RATING_META = {
    1: ("Tentative", "#b91c1c", "#fef2f2"),
    2: ("Plausible", "#b45309", "#fffbeb"),
    3: ("Confident", "#047857", "#ecfdf5"),
    4: ("Definitive", "#065f46", "#ecfdf5"),
}


# --------------------------------------------------------------------------- #
# Anthropic plumbing
# --------------------------------------------------------------------------- #
@st.cache_resource
def get_client() -> Anthropic:
    return Anthropic()


def stream_analysis(image_block: dict):
    """Yield text chunks from Claude as the analysis is generated."""
    client = get_client()
    content = [image_block, {"type": "text", "text": PROMPT}]
    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def parse_rating(text: str):
    """Best-effort extraction of the final 1-4 confidence rating from the response."""
    lowered = text.lower()

    # Prefer an explicit "rating ... N" near the end of the response.
    numeric = re.findall(r"rating[^0-9\n]{0,30}?([1-4])\b", lowered)
    if numeric:
        return int(numeric[-1])

    # Fall back to the named tiers ("Confident", "Definitive", ...).
    labels = {"tentative": 1, "plausible": 2, "confident": 3, "definitive": 4}
    last_pos, last_val = -1, None
    for word, val in labels.items():
        pos = lowered.rfind(word)
        if pos > last_pos:
            last_pos, last_val = pos, val
    return last_val


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Wildlife ID — Claude Vision", page_icon="🦊", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
      html, body, [class*="css"], .stMarkdown { font-family: 'Inter', system-ui, sans-serif; }
      .block-container { padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1120px; }
      #MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

      .hero-eyebrow { font-size: .8rem; font-weight: 600; letter-spacing: .14em;
        text-transform: uppercase; color: #047857; margin-bottom: .35rem; }
      .hero-title { font-size: 2.25rem; line-height: 1.1; font-weight: 800;
        letter-spacing: -0.025em; color: #0f172a; margin: 0 0 .4rem 0; }
      .hero-sub { color: #475569; font-size: 1.04rem; max-width: 640px; margin-bottom: .25rem; }
      .hr { height: 1px; background: linear-gradient(90deg,#e2e8f0,transparent);
        border: 0; margin: 1.5rem 0 1.25rem 0; }

      .badge { display: inline-flex; align-items: center; gap: .55rem; padding: .5rem .95rem;
        border-radius: 999px; font-weight: 600; font-size: .92rem; border: 1px solid #e2e8f0; }
      .badge .dot { width: .62rem; height: .62rem; border-radius: 999px; }
      .badge .tier { color: #64748b; font-weight: 500; }

      .loc-card { margin-top: .85rem; padding: .8rem .95rem; border: 1px solid #e2e8f0;
        border-radius: 12px; background: #f8fafc; }
      .loc-head { font-weight: 600; font-size: .9rem; color: #0f172a; }
      .loc-src { color: #94a3b8; font-weight: 500; font-size: .72rem; text-transform: uppercase;
        letter-spacing: .06em; margin-left: .35rem; }
      .loc-coords { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .95rem;
        color: #334155; margin: .35rem 0 .4rem; }
      .loc-link { font-size: .85rem; font-weight: 600; color: #047857; text-decoration: none; }
      .loc-link:hover { text-decoration: underline; }

      .meta { color: #94a3b8; font-size: .82rem; }
      .stButton > button { border-radius: 10px; font-weight: 600; padding: .55rem 1.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-eyebrow">Claude Vision · Messages API</div>
    <div class="hero-title">Wildlife Identification</div>
    <div class="hero-sub">Paste a public image URL or drop in a photo. Claude returns a
    structured field-guide analysis — subject, species, look-alikes, habitat, and a
    region estimate — with a calibrated confidence rating, plus exact GPS coordinates when the
    photo carries them.</div>
    """,
    unsafe_allow_html=True,
)

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(
        "**ANTHROPIC_API_KEY is not set.** Copy `.env.example` to `.env` and add your key, "
        "or set the environment variable, then reload."
    )
    st.stop()

st.markdown('<hr class="hr">', unsafe_allow_html=True)

source = st.radio(
    "Image source",
    ["🔗 Image URL", "⬆️ Upload a photo"],
    horizontal=True,
    label_visibility="collapsed",
)

image_block = None
display_image = None  # what st.image renders: a URL string or raw bytes

if source == "🔗 Image URL":
    url = st.text_input(
        "Public image URL",
        placeholder="https://www.nps.gov/cebr/learn/nature/images/RedFox_4.jpg",
        label_visibility="collapsed",
    )
    if url.strip():
        image_block = url_image_block(url.strip())
        display_image = url.strip()
else:
    uploaded = st.file_uploader(
        "Drag and drop a photo",
        type=SUPPORTED_TYPES,
        label_visibility="collapsed",
    )
    if uploaded is not None:
        data = uploaded.getvalue()
        image_block = bytes_image_block(data, uploaded.type or "image/jpeg")
        display_image = data

analyze = st.button("Analyze photo", type="primary", disabled=image_block is None)


def render_badge(slot, rating):
    if rating is None:
        return
    label, color, bg = RATING_META[rating]
    slot.markdown(
        f"""
        <div class="badge" style="background:{bg};">
          <span class="dot" style="background:{color};"></span>
          <span style="color:{color};">Confidence {rating}/4</span>
          <span class="tier">· {label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_location(gps, attempted):
    """Show EXIF GPS coordinates when present; otherwise point to Claude's inferred estimate."""
    if gps:
        altitude = f" · {gps['altitude_m']} m elev." if "altitude_m" in gps else ""
        st.markdown(
            f"""
            <div class="loc-card">
              <div class="loc-head">📍 Capture location
                <span class="loc-src">from photo EXIF</span></div>
              <div class="loc-coords">{gps['lat']}, {gps['lon']}{altitude}</div>
              <a class="loc-link" href="{gps['maps_url']}" target="_blank">View on map ↗</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif attempted:
        st.caption(
            "📍 No GPS metadata in this image — see the geographic estimate in the analysis."
        )


def render_results(
    display, blocks, stream: bool, gps=None, gps_attempted=False,
    saved_text: str = None, saved_rating=None,
):
    col_img, col_txt = st.columns([0.42, 0.58], gap="large")
    with col_img:
        st.image(display, use_container_width=True)
        badge_slot = st.empty()
        render_location(gps, gps_attempted)
    with col_txt:
        st.markdown("#### Analysis")
        box = st.container(border=True)
        with box:
            if stream:
                full_text = st.write_stream(stream_analysis(blocks))
            else:
                st.markdown(saved_text)
                full_text = saved_text
    rating = parse_rating(full_text) if stream else saved_rating
    render_badge(badge_slot, rating)
    return full_text, rating


if analyze:
    # Read the file's metadata for precise coordinates. For an upload we already hold the bytes;
    # for a URL we fetch them once, purely to inspect EXIF (Claude fetches the image separately).
    with st.spinner("Checking image metadata…"):
        if source == "🔗 Image URL":
            probe_bytes = fetch_image_bytes(url.strip())
        else:
            probe_bytes = data
        gps = extract_gps(probe_bytes) if probe_bytes else None
    try:
        text, rating = render_results(
            display_image, image_block, stream=True, gps=gps, gps_attempted=True,
        )
        st.session_state["last"] = {
            "display": display_image,
            "text": text,
            "rating": rating,
            "gps": gps,
        }
    except Exception as exc:  # noqa: BLE001 — surface any API/network error to the user
        st.error(f"Analysis failed: {exc}")
elif "last" in st.session_state:
    saved = st.session_state["last"]
    render_results(
        saved["display"], None, stream=False,
        gps=saved.get("gps"), gps_attempted=True,
        saved_text=saved["text"], saved_rating=saved["rating"],
    )

st.markdown(
    f'<p class="meta">Model: {MODEL} · Identifications are AI-generated and may be wrong — '
    "verify before relying on them.</p>",
    unsafe_allow_html=True,
)
