# Learn — Vision (image analysis)

A study sheet for the `vision/` example. Pair it with the runnable code: the notebook
([`wildlife_id.ipynb`](wildlife_id.ipynb)) for the guided walk-through, the Streamlit app
([`wildlife_id_app.py`](wildlife_id_app.py)) to experiment, and the CLI
([`run_url.py`](run_url.py)) for quick iteration.

**Where this fits in the CCA exam:** primarily **Prompt Engineering & Structured Output** (20%) —
designing a multi-step prompt that returns disciplined, calibrated output — with a secondary
touch of **Context & Reliability** (15%) via image token cost. See the
[STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

After working through this topic you should be able to:

- Send an image to Claude two ways — a **public URL** vs. **base64-encoded bytes** — and explain
  when each is appropriate.
- Structure a prompt that forces a **step-by-step analysis** and a **calibrated confidence
  rating** instead of an over-confident guess.
- Reason about **image token cost** and resolution, and why you downscale.
- Separate what the model can infer from **pixels** vs. what it cannot (e.g. precise location →
  EXIF metadata, not vision).

## Key concepts

- **Multimodal content blocks.** A user message's `content` is a list; you interleave
  `{"type": "image", ...}` blocks with `{"type": "text", ...}` blocks. Order matters — put the
  image before the question that refers to it.
- **Two image sources.**
  - `{"type": "url", "url": ...}` — Claude fetches the bytes itself; nothing lives on disk.
  - `{"type": "base64", "media_type": ..., "data": ...}` — you send the bytes (your own files).
- **Supported formats:** JPEG, PNG, GIF, WebP. There are per-image size/resolution limits and a
  cap on images per request — check the [vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
  for current exact numbers.
- **Token cost scales with pixels** (≈ width × height / 750). Very large images cost more without
  improving recognition — downscale (≈1568 px on the long edge is plenty for most tasks).
- **Calibrated output.** The example prompt asks for a 1–4 confidence rating and explicit
  look-alike reasoning. This is the transferable skill: make the model *show its evidence* and
  *quantify its certainty* rather than assert.

## API cheat-sheet

```python
from anthropic import Anthropic
client = Anthropic()

# Image from a public URL
url_block = {"type": "image", "source": {"type": "url", "url": "https://…/photo.jpg"}}

# Image from local bytes
import base64
b64 = base64.standard_b64encode(open("photo.jpg", "rb").read()).decode()
file_block = {"type": "image",
              "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}

resp = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": [url_block, {"type": "text", "text": "Identify the animal."}]}],
)
```

## Common pitfalls

- **Image after the question.** If the text references "the attached photo" but the image block
  comes later, results suffer. Put the image first (or be explicit about ordering).
- **Sending huge images.** Multi-MB, full-resolution photos burn tokens for no accuracy gain.
  Downscale before encoding.
- **Confusing pixels with metadata.** Claude reads the *image*; it cannot read EXIF GPS. Precise
  location comes from the file's metadata (see how `citations`/`documents` separate *inference*
  from *ground truth* — the same discipline applies here).
- **Over-trusting a confident answer.** A fluent ID can still be wrong (see the repo's
  De Brazza's-monkey-vs-chimpanzee case in `video/`). Always design for calibrated uncertainty.
- **Scanned/low-quality input.** Small, blurry, or occluded subjects cap accuracy regardless of
  model — cropping to the subject beats raising global resolution.

## Try it yourself

1. **URL → local.** Swap the example's `url_image_block(...)` for `image_block("your_photo.jpg")`
   and run it on a photo from your phone.
2. **Tighten the rubric.** Edit the prompt so the model must output **only** the species name and
   the numeric rating (no prose). What changes in reliability?
3. **Resolution experiment.** In `run_url.py`/the app, try a tiny vs. a large version of the same
   image. Does the confidence or the ID change? Relate it to token cost.
4. **Break it on purpose.** Feed an ambiguous or partially-occluded animal and confirm the model
   *lowers* its rating rather than guessing — that's the behavior you want.

## Check yourself

1. **When would you choose base64 over a URL for an image?**
   <details><summary>Answer</summary>When the image isn't reachable by a public URL — e.g. a local
   file, a user upload, or private data. URLs are convenient and keep things off disk, but Claude
   must be able to fetch them.</details>

2. **Roughly how does image token cost scale, and what's the practical implication?**
   <details><summary>Answer</summary>≈ (width × height) / 750 tokens. Large images cost a lot more
   without improving recognition, so downscale (≈1568 px long edge) before sending.</details>

3. **The model returns a confident species ID that's wrong. What prompt-design choice reduces the
   damage of this failure mode?**
   <details><summary>Answer</summary>Force calibrated output: require the model to cite the visual
   features behind the ID, list plausible look-alikes, and assign an explicit confidence rating —
   so low-evidence cases come back as low-confidence rather than confident-and-wrong.</details>

4. **Why can't vision answer "exactly where was this photo taken"?**
   <details><summary>Answer</summary>Precise coordinates live in the file's EXIF metadata, which
   the model never sees. Vision can only *estimate* a region from visual cues; exact location must
   be read from metadata separately.</details>

## Further reading

- [Vision — Claude API docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- [Messages API — content blocks](https://platform.claude.com/docs/en/api/messages)
