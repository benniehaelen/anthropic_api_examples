"""
Shared building blocks for the structured-outputs example.

Structured outputs make Claude return data that conforms to a schema you define, so you can feed
it straight into code without brittle parsing. The recommended path is `client.messages.parse(...)`
with a Pydantic model: the SDK enforces the schema and hands back a validated object
(`response.parsed_output`). Under the hood this uses `output_config.format` (JSON schema); you can
also use that directly, or `strict: True` on a tool's `input_schema` for guaranteed-valid tool
arguments.

The example extracts structured wildlife "sighting reports" from messy free-text field notes.
Imported by `structured_outputs.ipynb`, `extract_app.py`, and `run_extract.py`.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# Structured outputs work on all current models. Note: citations and structured outputs are
# mutually incompatible (enabling both 400s).
MODEL = "claude-sonnet-4-5"


class TimeOfDay(str, Enum):
    dawn = "dawn"
    day = "day"
    dusk = "dusk"
    night = "night"
    unknown = "unknown"


class SightingReport(BaseModel):
    """A structured wildlife sighting extracted from a free-text field note."""

    species: str = Field(description="Common name of the animal, best guess from the note.")
    scientific_name: Optional[str] = Field(
        default=None, description="Binomial name if determinable, else null."
    )
    count: int = Field(description="Number of individuals observed.")
    habitat: str = Field(description="Short description of the setting/habitat.")
    behaviors: List[str] = Field(description="Notable behaviors mentioned.")
    time_of_day: TimeOfDay = Field(description="Approximate time of day of the sighting.")
    confidence: int = Field(ge=1, le=5, description="How certain the note is about the species, 1-5.")


EXTRACT_PROMPT = (
    "Extract a structured wildlife sighting from the field note below. Fill every field as well as "
    "the note supports; use null for an unknown scientific name, and set confidence (1-5) to "
    "reflect how sure the note is about the species.\n\nField note:\n"
)

# Free-text field notes (test data) with the usual messiness: casual phrasing, hedged IDs, counts
# stated in words, times implied rather than given.
SAMPLE_NOTES = [
    "07:10, misty morning by the river — a single red fox trotting along the bank, paused to "
    "sniff, then slipped into the reeds. Pretty sure it was a fox: rusty coat, white tail tip.",
    "Around dusk we counted three mule deer grazing at the forest edge — two does and a fawn. "
    "They bolted the moment we stepped closer.",
    "Just after dark, heard then briefly glimpsed a barred owl high in an oak, calling over and "
    "over. Hard to be certain in the low light.",
    "Midday in the wetland: a pair of river otters sliding down the mudbank, hauling out and "
    "sliding again, very playful. Confident on the ID.",
]


def extract(client, note, max_tokens=1024):
    """Extract one note into a validated SightingReport using the Pydantic parse helper."""
    response = client.messages.parse(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": EXTRACT_PROMPT + note}],
        output_format=SightingReport,
    )
    return response.parsed_output


def extract_many(client, notes):
    """Extract a list of notes into a list of SightingReport objects."""
    return [extract(client, note) for note in notes]


# The raw JSON-schema form (no Pydantic), for reference. `messages.parse` is preferred, but this
# is the lower-level `output_config.format` it builds on. Note: the strict validator does not
# support numeric `minimum`/`maximum` — express bounded values with an `enum` instead.
SIGHTING_JSON_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "species": {"type": "string"},
            "count": {"type": "integer"},
            "confidence": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        },
        "required": ["species", "count", "confidence"],
        "additionalProperties": False,
    },
}
