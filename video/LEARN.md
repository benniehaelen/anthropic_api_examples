# Learn — Video (working within model constraints)

A study sheet for the `video/` example. Pair it with the notebook
([`animal_video_id.ipynb`](animal_video_id.ipynb)) and the CLI ([`run_video.py`](run_video.py)).

**Where this fits in the CCA exam:** primarily **Context & Reliability** (15%) — engineering around
a capability the API *doesn't* have, and managing cost/coverage trade-offs — with a touch of
**Agentic Architecture** (27%). See the [STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

- Explain why "video understanding" is built from **image frames**, not a video input.
- Sample frames so they cover the **whole clip**, and reason about the cost/coverage trade-off.
- Drive a **strict-JSON** per-frame response and fold it into a timeline.
- Know the accuracy ceiling: re-identification is approximate; framing beats resolution.

## Key concepts

- **No native video input.** The API takes images. So you decode a clip → sample frames →
  send them as an ordered, timestamp-labeled image sequence in one message.
- **Cover the whole clip.** Naively sampling "every N seconds from the start until max-frames"
  only sees the opening. For long/montage clips, spread `max_frames` **evenly across the full
  duration** (this repo's sampler does exactly that — a real bug we fixed).
- **Cost scales with frames × resolution.** Downscale frames (long edge ~768 px) and sample
  sparingly; image tokens ≈ (w × h)/750 per frame.
- **Temporal reasoning:** label each frame (`[frame i | t=Xs]`) so the model can reason about
  order and change; it reasons over the frames you send — it does **not** pixel-track.
- **Structured output for aggregation:** ask for strict JSON (species per frame), parse it, and
  build a per-species timeline in plain Python.
- **Accuracy ceiling:** small/occluded subjects cap recognition at any global resolution —
  cropping the subject (detector → crop → identify) beats raising resolution. Higher resolution
  mostly reduces *over*-confident wrong IDs.

## API cheat-sheet

```python
content = []
for i, (t, jpeg_bytes) in enumerate(frames):              # frames sampled across the WHOLE clip
    content.append({"type": "text", "text": f"[frame {i} | t={t:.1f}s]"})
    content.append({"type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg",
                               "data": base64.standard_b64encode(jpeg_bytes).decode()}})
content.append({"type": "text", "text": "Return JSON: species per frame + a summary."})
resp = client.messages.create(model="claude-sonnet-4-5", max_tokens=4096,
    messages=[{"role": "user", "content": content}])
```

## Common pitfalls

- **Sampling only the start.** The #1 mistake: a long montage shows different animals over time;
  start-only sampling reports just the first. Spread samples across the whole duration.
- **Too few frames.** Fast cuts get missed — raise `--max-frames` for montages.
- **Over-raising resolution.** It can't recover detail that isn't there (tiny/occluded subjects);
  crop instead.
- **Treating GIFs as a shortcut.** Extract frames explicitly rather than relying on the API to
  "play" an animated GIF.
- **Forgetting audio is invisible.** Vision can't hear calls/birdsong — that needs a separate
  audio model.
- **Fragile JSON parsing.** Models may vary JSON escaping; parse defensively (find the JSON span,
  `json.loads`), don't string-match.

## Try it yourself

1. **Coverage:** run a multi-animal montage with the default settings, then again with
   `--max-frames 20` — see more animals appear as coverage improves.
2. **Resolution:** rerun a hard clip with `--longest-side 1280`. Does a wrong-but-confident ID
   become a vaguer-but-honest one?
3. **Cadence:** change `--every-sec` and watch how the sampled timestamps (and cost) change.
4. **Timeline:** modify the prompt/schema to also capture behavior per frame, and extend the
   timeline builder.

## Check yourself

1. **A montage clearly has several animals but only one is reported. Most likely cause?**
   <details><summary>Answer</summary>The sampler only looked at the start of the clip. Spread the
   frame budget across the entire duration so later animals are captured.</details>

2. **Why send frames as images at all — why not the video file?**
   <details><summary>Answer</summary>The Claude API has no native video input; you decode the clip
   and send sampled frames as images.</details>

3. **Raising frame resolution didn't fix a misidentification of a small, caged animal. Why, and
   what helps more?**
   <details><summary>Answer</summary>Global resolution can't add detail that isn't resolvable when
   the subject is tiny/occluded. Cropping to the subject (detector → crop → identify) gives the
   model a high-detail view and helps far more.</details>

4. **How do you turn per-frame results into a per-species timeline reliably?**
   <details><summary>Answer</summary>Ask for strict JSON (species per labeled frame), parse it
   defensively, then aggregate in Python (first/last seen, frames, max count) — let the model do
   perception and code do the bookkeeping.</details>

## Further reading

- [Vision — Claude API docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- [Messages API — content blocks](https://platform.claude.com/docs/en/api/messages)
