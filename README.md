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

Examples are organized by topic under [`examples/`](examples/), one folder per Claude API
capability. Open a notebook with Jupyter (or the VS Code notebook editor) and run the cells
top to bottom.

### Vision

| Example | Description |
| --- | --- |
| [`vision/wildlife_id.ipynb`](examples/vision/wildlife_id.ipynb) | Identify wildlife in a photo with Claude's vision capability — subject detection, species ID, look-alikes, habitat cues, and a 1-4 confidence rating. Works with a public image URL or a local file. |
