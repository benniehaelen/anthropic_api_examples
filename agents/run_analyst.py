"""
Self-correcting analyst — command-line agent.

Orchestrator → analyst (runs code) ⇄ critic → synthesizer, over a CSV you provide. Prints the
multi-agent trace and the final report.

Usage (from the repo root):

    .venv\\Scripts\\python.exe agents/run_analyst.py --sample
    .venv\\Scripts\\python.exe agents/run_analyst.py --file data.csv -q "What drives revenue?"

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import argparse
import os
import sys
import tempfile

from anthropic import Anthropic
from dotenv import load_dotenv

from _analyst import (
    DEFAULT_QUESTION,
    OBSERVATIONS_CSV,
    orchestrate,
    upload_dataset,
    write_dataset,
)


def main():
    parser = argparse.ArgumentParser(description="Self-correcting multi-agent data analyst.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", "-f", help="CSV file to analyze")
    src.add_argument("--sample", action="store_true", help="use the built-in wildlife-survey CSV")
    parser.add_argument("--question", "-q", default=DEFAULT_QUESTION, help="the question to answer")
    parser.add_argument("--max-subtasks", type=int, default=3)
    parser.add_argument("--max-revisions", type=int, default=1)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    client = Anthropic()

    if args.sample:
        path = write_dataset(os.path.join(tempfile.gettempdir(), "observations.csv"))
        csv_text = OBSERVATIONS_CSV
    else:
        if not os.path.isfile(args.file):
            sys.exit(f"error: no such file: {args.file}")
        path = args.file
        with open(path, encoding="utf-8", errors="replace") as h:
            csv_text = h.read()

    def emit(e):
        k = e["kind"]
        if k == "plan":
            print("\n🧭 PLAN:")
            for i, s in enumerate(e["subtasks"], 1):
                print(f"   {i}. {s}")
        elif k == "subtask_start":
            print(f"\n🔎 {e['subtask']}")
        elif k == "analyst":
            print(f"   🔬 analyst (attempt {e['attempt']}): {e['finding'][:120].replace(chr(10), ' ')}…")
        elif k == "critic":
            print("   ✅ critic: passed" if e["passed"]
                  else f"   ♻️ critic: revise — {'; '.join(e['issues'])}")
        elif k == "synthesizing":
            print("\n🧩 synthesizing…")

    file_id = upload_dataset(client, path).id
    out = orchestrate(client, args.question, file_id, csv_text,
                      max_subtasks=args.max_subtasks, max_revisions=args.max_revisions, emit=emit)

    print("\n" + "=" * 60 + "\nFINAL REPORT\n" + "=" * 60)
    print(out["final"])


if __name__ == "__main__":
    main()
