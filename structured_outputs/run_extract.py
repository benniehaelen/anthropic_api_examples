"""
Structured outputs — command-line extractor.

Extract schema-valid wildlife sighting records from free-text field notes and print them as JSON.

Usage (from the repo root):

    .venv\\Scripts\\python.exe structured_outputs/run_extract.py --sample
    .venv\\Scripts\\python.exe structured_outputs/run_extract.py --file notes.txt   # one note per line

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import argparse
import json
import sys

from anthropic import Anthropic
from dotenv import load_dotenv

from _structured_outputs import SAMPLE_NOTES, extract


def main():
    parser = argparse.ArgumentParser(description="Extract structured sightings from field notes.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", "-f", help="text file with one field note per line")
    src.add_argument("--sample", action="store_true", help="use the built-in sample notes")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    client = Anthropic()

    if args.sample:
        notes = SAMPLE_NOTES
    else:
        with open(args.file, encoding="utf-8") as handle:
            notes = [line.strip() for line in handle if line.strip()]

    records = []
    for i, note in enumerate(notes, start=1):
        try:
            report = extract(client, note)
            records.append(report.model_dump(mode="json"))
            print(f"[{i}/{len(notes)}] {report.species} (x{report.count}, conf {report.confidence})")
        except Exception as exc:  # noqa: BLE001 — report and continue
            print(f"[{i}/{len(notes)}] failed: {exc}")

    print("\n" + json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
