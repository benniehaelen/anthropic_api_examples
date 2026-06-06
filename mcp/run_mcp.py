"""
MCP — command-line demo.

Spawns the local MCP server (`server.py`), exposes its tools to Claude via the SDK's MCP helpers
+ tool runner, and answers your question — printing which MCP tools were called.

Usage (from the repo root):

    .venv\\Scripts\\python.exe mcp/run_mcp.py
    .venv\\Scripts\\python.exe mcp/run_mcp.py -q "Compare the red fox and gray wolf, with sighting counts."

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root) and `pip install "anthropic[mcp]" mcp`.
"""

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from _mcp_demo import run_query

DEFAULT_QUESTION = "What can you tell me about the river otter, and how many sightings does it have?"


def main():
    parser = argparse.ArgumentParser(description="Use tools from a local MCP server via Claude.")
    parser.add_argument("--question", "-q", default=DEFAULT_QUESTION, help="the question to ask")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    result = asyncio.run(run_query(args.question))

    print("MCP tools available:", ", ".join(result["tools"]))
    print("\n── transcript ──")
    for e in result["transcript"]:
        if e["kind"] == "text":
            if e["text"].strip():
                print("assistant:", e["text"])
        else:
            print(f"  → MCP tool {e['name']}({e['input']})")

    print("\n── answer ──")
    print(result["final"])


if __name__ == "__main__":
    main()
