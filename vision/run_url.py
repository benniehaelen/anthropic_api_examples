"""
Run the wildlife identification analysis on a single image from the command line.

Usage (from the repo root):

    .venv\\Scripts\\python.exe vision/run_url.py <image-url-or-path>

Examples:

    .venv\\Scripts\\python.exe vision/run_url.py https://images6.alphacoders.com/528/thumb-1920-528080.jpg
    .venv\\Scripts\\python.exe vision/run_url.py my_photo.jpg
    .venv\\Scripts\\python.exe vision/run_url.py my_photo.jpg --no-location

Requires ANTHROPIC_API_KEY in your environment or a .env file at the repo root.
"""

import argparse
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

# Python puts this script's folder (vision/) on sys.path, so the shared module imports directly.
from _wildlife import (
    MODEL,
    PROMPT,
    bytes_image_block,
    extract_gps,
    fetch_image_bytes,
    reverse_geocode,
    url_image_block,
)

MAX_TOKENS = 4000
MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def is_url(value):
    return value.lower().startswith(("http://", "https://"))


def build_image(image_arg):
    """Return (content_block, raw_bytes_or_None) for a URL or a local file path."""
    if is_url(image_arg):
        # Claude fetches the URL itself for analysis; we download the bytes only to read EXIF.
        return url_image_block(image_arg), fetch_image_bytes(image_arg)

    path = Path(image_arg)
    if not path.is_file():
        sys.exit(f"error: no such file: {path}  (and it is not an http(s) URL)")
    media_type = MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        sys.exit(f"error: unsupported image type '{path.suffix}'. Use one of {sorted(MEDIA_TYPES)}.")
    raw = path.read_bytes()
    return bytes_image_block(raw, media_type), raw


def describe_location(raw_bytes):
    """Print precise coordinates from EXIF when present, with a resolved place name."""
    print("\nLocation")
    print("-" * 60)
    gps = extract_gps(raw_bytes) if raw_bytes else None
    if not gps:
        print("No GPS metadata in this image — see the geographic estimate in the analysis above.")
        return
    place = reverse_geocode(gps["lat"], gps["lon"])
    if place:
        print(f"Place:       {place}  (© OpenStreetMap contributors)")
    print(f"Coordinates: {gps['lat']}, {gps['lon']}")
    if "altitude_m" in gps:
        print(f"Altitude:    {gps['altitude_m']} m")
    print(f"Map:         {gps['maps_url']}")


def main():
    parser = argparse.ArgumentParser(description="Identify wildlife in an image with Claude.")
    parser.add_argument("image", help="public image URL or path to a local image file")
    parser.add_argument(
        "--no-location",
        action="store_true",
        help="skip reading EXIF GPS / reverse geocoding",
    )
    args = parser.parse_args()

    # Print UTF-8 so em-dashes etc. don't choke a legacy Windows console.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    client = Anthropic()  # raises a clear error if ANTHROPIC_API_KEY is missing

    image_block, raw_bytes = build_image(args.image)

    print(f"Analyzing: {args.image}")
    print(f"Model:     {MODEL}\n")
    print("Analysis")
    print("-" * 60)
    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": [image_block, {"type": "text", "text": PROMPT}]}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print()

    if not args.no_location:
        describe_location(raw_bytes)


if __name__ == "__main__":
    main()
