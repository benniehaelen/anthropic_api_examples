# Anthropic API examples

A growing collection of self-contained examples for the [Anthropic API](https://docs.anthropic.com/),
using the official `anthropic` Python SDK.

## Setup

The repo includes a Python 3.14 virtual environment in `.venv/`. On Windows / PowerShell:

```powershell
# Install dependencies into the venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Provide your API key
copy .env.example .env
# then edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

Each example loads the key from `.env` via `python-dotenv`, so you only configure it once.

## Examples

Examples are organized into top-level topic folders, one per Claude API capability. Open a
notebook with Jupyter (or the VS Code notebook editor) and run the cells top to bottom.

### Vision

| Example | Description |
| --- | --- |
| [`vision/wildlife_id.ipynb`](vision/wildlife_id.ipynb) | Identify wildlife in a photo with Claude's vision capability — subject detection, species ID, look-alikes, habitat cues, a region estimate, and a 1-4 confidence rating. Also reads precise GPS coordinates from the photo's EXIF metadata when present and resolves them to a place name. Works with a public image URL or a local file. |
| [`vision/wildlife_id_app.py`](vision/wildlife_id_app.py) | A Streamlit front end for the wildlife analysis above: paste an image URL or drag in a photo, watch the analysis stream in, and see the confidence rating as a color-coded badge plus a location card (EXIF GPS coordinates + place name when available, Claude's inferred region otherwise). |

Run the Streamlit app (from the repo root):

```powershell
.venv\Scripts\python.exe -m streamlit run vision/wildlife_id_app.py
```

Place names are resolved with the [OpenStreetMap Nominatim](https://nominatim.org/) service
(no API key required) and are © OpenStreetMap contributors. Nominatim asks callers to stay
under ~1 request/second; for heavy use, run your own instance or a paid geocoder.
