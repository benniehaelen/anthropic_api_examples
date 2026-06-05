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
