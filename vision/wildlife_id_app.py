"""
Wildlife identification — Streamlit app.

A polished front end for the same analysis as `wildlife_id.ipynb`: paste a public image
URL or drag in a photo, and Claude's vision capability returns a structured identification
(subject detection, species ID, look-alikes, habitat cues) plus a 1-4 confidence rating.

Run it (Windows / PowerShell, from the repo root):

    .venv\\Scripts\\python.exe -m streamlit run vision/wildlife_id_app.py

Requires ANTHROPIC_API_KEY in your environment or a .env file at the repo root.
"""

import os
import re

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 4000
SUPPORTED_TYPES = ["jpg", "jpeg", "png", "gif", "webp"]

PROMPT = """
Analyze the attached wildlife photo with these specific steps. Identify only what the image
actually supports, and say so plainly when a feature is obscured or ambiguous.

1. Subject detection: Establish what is in the frame:
   - How many animals are present and where they sit in the frame
   - How much of each animal is visible (full body, head only, partially occluded)
   - Overall image quality factors that affect identification (lighting, focus, distance)

2. Identification: Name the animal as precisely as the image allows:
   - The most likely common name, and the species (binomial name) if you are confident enough
   - The specific visual features that drive the identification (coat color and pattern, ear
     shape, snout, tail, leg markings, relative size, body proportions)

3. Alternatives and confounders: Guard against overconfidence:
   - List the most plausible look-alike species
   - For each, name the feature in the photo that argues for or against it

4. Habitat and context cues: Read the surroundings:
   - Describe the environment, substrate, vegetation, and the animal's posture or behavior
   - Note what these cues suggest about the setting or the animal's identity

5. Identification Confidence Rating: Assign a rating from 1-4:
   - Rating 1 (Tentative): Only a broad category is supportable (for example, "a canid");
     key diagnostic features are obscured.
   - Rating 2 (Plausible): A likely species, but strong look-alikes cannot be ruled out.
   - Rating 3 (Confident): Species identification is well supported by multiple distinguishing
     features.
   - Rating 4 (Definitive): Unambiguous; diagnostic features are clearly visible and no
     realistic alternative remains.

For each item above (1-5), write one sentence summarizing your findings, with your final
response being the numeric Identification Confidence Rating (1-4) with a brief justification.
"""

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


def url_image_block(url: str) -> dict:
    return {"type": "image", "source": {"type": "url", "url": url}}


def bytes_image_block(data: bytes, media_type: str) -> dict:
    import base64

    encoded = base64.standard_b64encode(data).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": encoded},
    }


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
    structured field-guide analysis — subject, species, look-alikes, habitat — with a calibrated
    confidence rating.</div>
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


def render_results(display, blocks, stream: bool, saved_text: str = None, saved_rating=None):
    col_img, col_txt = st.columns([0.42, 0.58], gap="large")
    with col_img:
        st.image(display, use_container_width=True)
        badge_slot = st.empty()
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
    try:
        text, rating = render_results(display_image, image_block, stream=True)
        st.session_state["last"] = {
            "display": display_image,
            "text": text,
            "rating": rating,
        }
    except Exception as exc:  # noqa: BLE001 — surface any API/network error to the user
        st.error(f"Analysis failed: {exc}")
elif "last" in st.session_state:
    saved = st.session_state["last"]
    render_results(
        saved["display"], None, stream=False,
        saved_text=saved["text"], saved_rating=saved["rating"],
    )

st.markdown(
    f'<p class="meta">Model: {MODEL} · Identifications are AI-generated and may be wrong — '
    "verify before relying on them.</p>",
    unsafe_allow_html=True,
)
