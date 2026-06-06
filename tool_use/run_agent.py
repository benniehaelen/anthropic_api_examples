"""
Tool use — command-line agent.

Ask a question; Claude calls custom tools (calculator, get_weather) in a loop to answer. Prints
the step-by-step transcript and the final answer.

Usage (from the repo root):

    .venv\\Scripts\\python.exe tool_use/run_agent.py -q "Weather in Tokyo, and 100 - 32?"

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import argparse
import sys

from anthropic import Anthropic
from dotenv import load_dotenv

from _tool_use import run_loop


def main():
    parser = argparse.ArgumentParser(description="Ask Claude a question answered via custom tools.")
    parser.add_argument("--question", "-q", required=True, help="the question to answer")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    final, transcript = run_loop(Anthropic(), args.question)

    print("── transcript ──")
    for e in transcript:
        if e["kind"] == "text":
            if e["text"].strip():
                print("assistant:", e["text"])
        elif e["kind"] == "tool_call":
            print(f"  → {e['name']}({', '.join(f'{k}={v!r}' for k, v in e['input'].items())})")
        elif e["kind"] == "tool_result":
            print(f"  ← {e['content']}" + ("  [error]" if e["is_error"] else ""))

    print("\n── answer ──")
    print(final)


if __name__ == "__main__":
    main()
