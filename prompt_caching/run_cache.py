"""
Prompt caching — command-line demo.

Runs a batch of questions against a large cached prefix and prints the per-request usage so you
can see the write-then-read pattern. With --compare it runs the batch twice (uncached, then
cached) and reports the savings.

Usage (from the repo root):

    .venv\\Scripts\\python.exe prompt_caching/run_cache.py
    .venv\\Scripts\\python.exe prompt_caching/run_cache.py --compare
    .venv\\Scripts\\python.exe prompt_caching/run_cache.py --volatile   # break the cache on purpose

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import argparse
import sys

from anthropic import Anthropic
from dotenv import load_dotenv

from _prompt_caching import (
    QUESTIONS,
    ask,
    prefix_token_count,
    relative_input_cost,
    usage_of,
)


def run_batch(client, questions, cache, volatile):
    rows = []
    for i, q in enumerate(questions):
        vp = f"Request time: 2026-06-06T12:00:{i:02d}Z" if volatile else None
        resp, secs = ask(client, q, cache=cache, volatile_prefix=vp)
        rows.append((q, usage_of(resp), secs))
    return rows


def print_table(rows):
    print(f"{'question':<46} {'input':>6} {'write':>6} {'read':>6} {'lat(s)':>7} {'relcost':>8}")
    for q, u, secs in rows:
        print(f"{q[:44]:<46} {u['input']:>6} {u['cache_write']:>6} {u['cache_read']:>6} "
              f"{secs:>7.2f} {relative_input_cost(u):>8.2f}")


def main():
    parser = argparse.ArgumentParser(description="Demonstrate and measure prompt caching.")
    parser.add_argument("-n", "--questions", type=int, default=len(QUESTIONS),
                        help=f"how many questions to run (max {len(QUESTIONS)})")
    parser.add_argument("--no-cache", action="store_true", help="disable caching")
    parser.add_argument("--volatile", action="store_true",
                        help="inject a changing prefix to defeat the cache (the classic bug)")
    parser.add_argument("--compare", action="store_true",
                        help="run uncached then cached and report the savings")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    client = Anthropic()
    questions = QUESTIONS[: args.questions]

    print(f"Cacheable prefix: {prefix_token_count(client):,} tokens\n")

    if args.compare:
        print("== Uncached ==")
        uncached = run_batch(client, questions, cache=False, volatile=False)
        print_table(uncached)
        print("\n== Cached ==")
        cached = run_batch(client, questions, cache=True, volatile=False)
        print_table(cached)
        read = sum(u["cache_read"] for _, u, _ in cached)
        full_uncached = sum(u["input"] for _, u, _ in uncached)
        print(f"\nTokens served from cache: {read:,} of {full_uncached:,} prompt tokens "
              f"({read / full_uncached:.0%}) moved to ~0.1x price.")
    else:
        print_table(run_batch(client, questions, cache=not args.no_cache, volatile=args.volatile))


if __name__ == "__main__":
    main()
