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
| [`vision/run_url.py`](vision/run_url.py) | A command-line runner for the same analysis: pass a URL or local image path, stream the result to your terminal, and print the location (EXIF GPS + place name, or a note that none is present). |

Run the Streamlit app (from the repo root):

```powershell
.venv\Scripts\python.exe -m streamlit run vision/wildlife_id_app.py
```

Or run a single image from the command line:

```powershell
.venv\Scripts\python.exe vision/run_url.py https://example.com/photo.jpg
.venv\Scripts\python.exe vision/run_url.py my_photo.jpg --no-location
```

Place names are resolved with the [OpenStreetMap Nominatim](https://nominatim.org/) service
(no API key required) and are © OpenStreetMap contributors. Nominatim asks callers to stay
under ~1 request/second; for heavy use, run your own instance or a paid geocoder.

### Video

The Claude API takes images, not video — so these examples decode a clip into sampled,
timestamp-labeled frames, analyze them as one sequence, and report a per-species timeline.
Frame decoding uses OpenCV.

| Example | Description |
| --- | --- |
| [`video/animal_video_id.ipynb`](video/animal_video_id.ipynb) | Identify animals across a short video: sample frames at a fixed interval, send them to Claude as one ordered sequence, and collapse the per-frame JSON into a per-species timeline (first/last seen, frames, max count). |
| [`video/run_video.py`](video/run_video.py) | A command-line runner for the same analysis: pass a video URL or local path, and print the summary plus the per-species timeline. |

Run a video from the command line (from the repo root):

```powershell
.venv\Scripts\python.exe video/run_video.py clip.mp4
.venv\Scripts\python.exe video/run_video.py https://example.com/clip.mp4 --every-sec 0.5 --max-frames 30
.venv\Scripts\python.exe video/run_video.py clip.mp4 --longest-side 1280   # more frame detail, more tokens
```

Frames are downscaled to `--longest-side` pixels (default 768) to control image-token cost.
Raising it gives the model more detail, but it can't compensate for a subject that is small or
occluded in the frame — for hard species IDs, cropping the animal before sending it is far more
effective than raising global resolution.
