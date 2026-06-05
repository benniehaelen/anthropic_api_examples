"""
Identify animals in a short video from the command line.

Decodes the clip into a few sampled frames, sends them to Claude as one ordered sequence, and
prints a summary plus a per-species timeline.

Usage (from the repo root):

    .venv\\Scripts\\python.exe video/run_video.py <video-url-or-path>
    .venv\\Scripts\\python.exe video/run_video.py clip.mp4 --every-sec 0.5 --max-frames 30

Requires ANTHROPIC_API_KEY in your environment or a .env file at the repo root.
"""

import argparse
import os
import sys

from anthropic import Anthropic
from dotenv import load_dotenv

# Python puts this script's folder (video/) on sys.path, so the shared module imports directly.
from _video import (
    MODEL,
    analyze_frames,
    build_timeline,
    fetch_video_to_temp,
    format_timeline,
    sample_frames,
)


def is_url(value):
    return value.lower().startswith(("http://", "https://"))


def main():
    parser = argparse.ArgumentParser(description="Identify animals in a short video with Claude.")
    parser.add_argument("video", help="public video URL or path to a local video file")
    parser.add_argument("--every-sec", type=float, default=1.0, help="sample one frame every N seconds (default 1.0)")
    parser.add_argument("--max-frames", type=int, default=10, help="cap on frames sent to Claude (default 10)")
    parser.add_argument("--longest-side", type=int, default=768, help="downscale frames to this many pixels on the longest side (default 768; higher = more detail and more tokens)")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    client = Anthropic()  # raises a clear error if ANTHROPIC_API_KEY is missing

    # Resolve the input to a local file path (download URLs to a temp file, then clean up).
    temp_path = None
    if is_url(args.video):
        print(f"Downloading {args.video} …")
        source = temp_path = fetch_video_to_temp(args.video)
    else:
        source = args.video
        if not os.path.isfile(source):
            sys.exit(f"error: no such file: {source}  (and it is not an http(s) URL)")

    try:
        frames = sample_frames(
            source, every_sec=args.every_sec, max_frames=args.max_frames,
            longest_side=args.longest_side,
        )
        print(f"Sampled {len(frames)} frames (every {args.every_sec}s, {args.longest_side}px) · model {MODEL}")
        print(f"Analyzing frames t={frames[0][0]:.1f}s … t={frames[-1][0]:.1f}s …\n")

        result = analyze_frames(client, frames)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    print("Summary")
    print("-" * 60)
    print(result.get("summary", "(no summary returned)"))

    print("\nPer-species timeline")
    print("-" * 60)
    print(format_timeline(build_timeline(result)))


if __name__ == "__main__":
    main()
