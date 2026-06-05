"""
Shared building blocks for the animal-in-video example.

The Claude API has no native video input — it takes images. So this module decodes a clip into
a handful of sampled frames, sends them to Claude as one ordered, timestamp-labeled image
sequence, and turns the model's per-frame answer into a per-species timeline.

Imported by both `animal_video_id.ipynb` and the CLI runner `run_video.py`.
"""

import base64
import json

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 4000

# We ask for strict JSON so the result can be turned into a timeline deterministically. Each
# frame is labeled "[frame i | t=Xs]" in the message, and the model echoes those timestamps back.
PROMPT = """You are given an ordered sequence of still frames sampled from a short wildlife
video. Each frame is preceded by a text label like "[frame 3 | t=6.0s]".

Identify the animals visible across the frames and how they change over time. Reason across the
whole sequence, not just frame by frame. Be conservative: only report a species when a frame
actually supports it, and do not invent animals in frames where none are clearly visible. Use
the same common_name spelling every time a species reappears, so it can be tracked across frames.

Respond with ONLY a JSON object — no markdown fences, no commentary — of this exact shape:

{
  "frames": [
    {"t": <seconds as a number>, "species": [
        {"common_name": <string>, "scientific_name": <string or null>, "count": <integer>}
    ]}
  ],
  "summary": <one or two sentences describing what happens across the clip>
}

Include one entry in "frames" for every labeled frame, in order. If a frame shows no identifiable
animal, give it an empty "species" list."""


# --------------------------------------------------------------------------- #
# Frame sampling (OpenCV)
# --------------------------------------------------------------------------- #
def _encode_jpeg(frame, longest_side, quality):
    """Downscale a BGR frame to `longest_side` and return JPEG bytes (smaller = cheaper tokens)."""
    import cv2

    height, width = frame.shape[:2]
    scale = longest_side / max(height, width)
    if scale < 1:
        frame = cv2.resize(
            frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA
        )
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("failed to JPEG-encode a video frame")
    return buffer.tobytes()


def sample_frames(path, every_sec=1.0, max_frames=20, longest_side=768, jpeg_quality=80):
    """Sample frames so they cover the WHOLE clip, not just its first seconds.

    Returns a list of (timestamp_seconds, jpeg_bytes), at most `max_frames` long.

    - Short clips (duration <= max_frames * every_sec): one frame every `every_sec` seconds.
    - Long clips: `max_frames` frames spread evenly across the entire duration, so a montage
      that shows a different animal every few seconds is actually covered. This is the key to
      not missing animals that appear later in the video.

    Falls back to sequential interval sampling when the container doesn't report a frame count.
    """
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"could not open video: {path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    interval = max(1, int(round(fps * every_sec)))

    def grab(index):
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if not ok:
            return None
        return round(index / fps, 2), _encode_jpeg(frame, longest_side, jpeg_quality)

    frames = []
    if total > 0:
        if total <= interval * max_frames:
            indices = list(range(0, total, interval))  # short clip: dense interval, full coverage
        elif max_frames == 1:
            indices = [total // 2]
        else:
            # Spread max_frames evenly from the first to the last frame.
            indices = [round(i * (total - 1) / (max_frames - 1)) for i in range(max_frames)]
        for index in indices:
            got = grab(index)
            if got is not None:
                frames.append(got)
    else:
        # Unknown length: read sequentially and keep one every `interval` frames (covers the start).
        index = 0
        while len(frames) < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            if index % interval == 0:
                frames.append((round(index / fps, 2), _encode_jpeg(frame, longest_side, jpeg_quality)))
            index += 1

    capture.release()
    if not frames:
        raise RuntimeError(f"no frames could be read from: {path}")
    return frames


def frames_to_content(frames):
    """Build the Messages API content list: a timestamp label + image block per frame, then the prompt."""
    content = []
    for i, (timestamp, jpeg) in enumerate(frames):
        content.append({"type": "text", "text": f"[frame {i} | t={timestamp:.1f}s]"})
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(jpeg).decode("utf-8"),
                },
            }
        )
    content.append({"type": "text", "text": PROMPT})
    return content


# A descriptive User-Agent. Some hosts (e.g. Wikimedia) return 403 for the default httpx
# agent, so identify the tool per their usage policies.
USER_AGENT = (
    "anthropic-api-examples/video "
    "(https://github.com/benniehaelen/anthropic_api_examples)"
)


def fetch_video_to_temp(url, timeout=60):
    """Download a video URL to a temporary file and return its path (OpenCV needs a real path)."""
    import os
    import tempfile

    import httpx

    suffix = os.path.splitext(url.split("?")[0])[1] or ".mp4"
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        with httpx.stream(
            "GET", url, timeout=timeout, follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_bytes():
                handle.write(chunk)
    except Exception:
        handle.close()
        if os.path.exists(handle.name):
            os.remove(handle.name)
        raise
    finally:
        handle.close()
    return handle.name


# --------------------------------------------------------------------------- #
# Analysis + timeline
# --------------------------------------------------------------------------- #
def parse_json(text):
    """Parse the model's JSON reply, tolerating stray prose or code fences around it."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def analyze_frames(client, frames):
    """Send the sampled frames to Claude in one request and return the parsed JSON result."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": frames_to_content(frames)}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    return parse_json(text)


def build_timeline(result):
    """Collapse the per-frame detections into {species: {times, max_count, scientific_name}}."""
    timeline = {}
    for frame in result.get("frames", []):
        timestamp = frame.get("t")
        for entry in frame.get("species", []) or []:
            name = entry.get("common_name")
            if not name:
                continue
            record = timeline.setdefault(
                name, {"times": [], "max_count": 0, "scientific_name": entry.get("scientific_name")}
            )
            if timestamp is not None:
                record["times"].append(timestamp)
            record["max_count"] = max(record["max_count"], entry.get("count") or 1)
            if not record["scientific_name"] and entry.get("scientific_name"):
                record["scientific_name"] = entry["scientific_name"]
    for record in timeline.values():
        record["times"] = sorted(set(record["times"]))
    return timeline


def format_timeline(timeline):
    """Render the timeline dict as a readable text block."""
    if not timeline:
        return "No animals were identified in the sampled frames."
    lines = []
    # Order species by first appearance.
    for name, record in sorted(timeline.items(), key=lambda kv: (kv[1]["times"] or [0])[0]):
        times = record["times"]
        sci = f" ({record['scientific_name']})" if record.get("scientific_name") else ""
        span = (
            f"{times[0]:.1f}s" if len(times) == 1 else f"{times[0]:.1f}s–{times[-1]:.1f}s"
        )
        seen_at = ", ".join(f"{t:.1f}s" for t in times)
        lines.append(
            f"{name}{sci}\n    seen {span} · max count {record['max_count']} · frames @ {seen_at}"
        )
    return "\n".join(lines)
