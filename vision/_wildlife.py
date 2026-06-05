"""
Shared building blocks for the wildlife-identification examples.

Imported by both the notebook (`wildlife_id.ipynb`) and the Streamlit app
(`wildlife_id_app.py`) so the model choice, the analysis prompt, and the image-block
helpers live in exactly one place and cannot drift apart.
"""

import base64

MODEL = "claude-sonnet-4-5"

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

5. Geographic origin (visual estimate): Infer where the photo was most likely taken, using only
   visual evidence — the species' native range, vegetation, terrain, geology, snow, and light.
   Give the broadest region you are confident in (for example, continent or biome) and narrow it
   only as far as the evidence honestly allows. State this plainly as an estimate and name the
   cues behind it. Do not invent a specific place, park, or coordinates — this is inference from
   the image, not a GPS reading.

6. Identification Confidence Rating: Assign a rating from 1-4:
   - Rating 1 (Tentative): Only a broad category is supportable (for example, "a canid");
     key diagnostic features are obscured.
   - Rating 2 (Plausible): A likely species, but strong look-alikes cannot be ruled out.
   - Rating 3 (Confident): Species identification is well supported by multiple distinguishing
     features.
   - Rating 4 (Definitive): Unambiguous; diagnostic features are clearly visible and no
     realistic alternative remains.

For each item above (1-6), write one sentence summarizing your findings, with your final
response being the numeric Identification Confidence Rating (1-4) with a brief justification.
"""


def url_image_block(url):
    """Wrap a public image URL as an Anthropic image content block.
    Claude fetches the bytes itself, so nothing needs to live on disk."""
    return {"type": "image", "source": {"type": "url", "url": url}}


def image_block(path, media_type="image/jpeg"):
    """Wrap a local image file as a base64 image content block.
    Use this for your own photos that are not reachable by URL."""
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def bytes_image_block(data, media_type="image/jpeg"):
    """Wrap raw image bytes (e.g. a Streamlit upload) as a base64 image content block."""
    encoded = base64.standard_b64encode(data).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": encoded},
    }


# --------------------------------------------------------------------------- #
# Location: precise coordinates from EXIF metadata
#
# Claude reads the image *pixels* and can only *estimate* a region from them (step 5 of the
# prompt). Precise coordinates, when they exist, live in the file's EXIF metadata — which Claude
# never sees — so we parse them ourselves. Note that most images published on the web have had
# their EXIF (and therefore any GPS) stripped, so absence of coordinates is the common case.
# --------------------------------------------------------------------------- #
GPSINFO_IFD = 0x8825  # EXIF tag id for the GPS sub-IFD (stable across Pillow versions)


def fetch_image_bytes(url, timeout=30):
    """Download image bytes from a URL so EXIF can be read locally. Returns bytes or None.

    Claude fetches a URL image on its own for analysis; this separate fetch only exists so we
    can inspect the file's metadata, which the API response does not expose.
    """
    import httpx

    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None


def extract_gps(data):
    """Extract GPS coordinates from image EXIF metadata.

    Returns a dict with 'lat', 'lon', and 'maps_url' (plus 'altitude_m' when present), or
    None if the image carries no usable GPS metadata.
    """
    import io

    from PIL import ExifTags, Image

    try:
        exif = Image.open(io.BytesIO(data)).getexif()
        gps = exif.get_ifd(GPSINFO_IFD)
    except Exception:
        return None
    if not gps:
        return None

    tags = {ExifTags.GPSTAGS.get(key, key): value for key, value in gps.items()}

    def to_decimal(coord, ref):
        degrees, minutes, seconds = (float(part) for part in coord)
        decimal = degrees + minutes / 60 + seconds / 3600
        return -decimal if str(ref).upper().startswith(("S", "W")) else decimal

    try:
        lat = to_decimal(tags["GPSLatitude"], tags.get("GPSLatitudeRef", "N"))
        lon = to_decimal(tags["GPSLongitude"], tags.get("GPSLongitudeRef", "E"))
    except (KeyError, TypeError, ValueError):
        return None

    result = {
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "maps_url": f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}",
    }

    altitude = tags.get("GPSAltitude")
    if altitude is not None:
        try:
            meters = float(altitude)
            if tags.get("GPSAltitudeRef") in (1, b"\x01"):  # 1 = below sea level
                meters = -meters
            result["altitude_m"] = round(meters, 1)
        except (TypeError, ValueError):
            pass

    return result
