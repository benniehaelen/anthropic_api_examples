"""Command-line demo for the advisor tool (beta).

Run a task with an executor + advisor pair, print the transcript with
advice highlighted, and show the per-iteration usage breakdown. With
--compare, run the same task executor-alone first and report the delta.

Examples (from the repo root, Windows / PowerShell):

    .venv\\Scripts\\python.exe advisor/run_advisor.py
    .venv\\Scripts\\python.exe advisor/run_advisor.py --compare
    .venv\\Scripts\\python.exe advisor/run_advisor.py -q "Plan a migration of a cron-based ETL job to an event-driven design" --advisor-max-tokens 2048 --brevity
    .venv\\Scripts\\python.exe advisor/run_advisor.py --compare --rates 3 15 15 75
"""

from __future__ import annotations

import argparse
import sys

from _advisor import (
    DEFAULT_ADVISOR,
    DEFAULT_EXECUTOR,
    DEFAULT_TASK,
    SUGGESTED_SYSTEM_PROMPT,
    estimate_cost,
    extract_advisor_events,
    final_text,
    get_client,
    make_advisor_tool,
    run_turn,
    summarize_usage,
    with_brevity_hint,
)

RULE = "-" * 72


def print_transcript(response) -> None:
    for block in response.content:
        btype = getattr(block, "type", None)
        if btype == "text":
            print(block.text)
        elif btype == "server_tool_use" and getattr(block, "name", "") == "advisor":
            print(f"\n[executor consults the advisor]")
        elif btype == "advisor_tool_result":
            content = block.content
            ctype = getattr(content, "type", None)
            if ctype == "advisor_result":
                truncated = getattr(content, "stop_reason", None) == "max_tokens"
                flag = " (TRUNCATED at max_tokens cap)" if truncated else ""
                print(f"\n[advisor]{flag}\n{content.text}\n")
            elif ctype == "advisor_redacted_result":
                print("\n[advisor returned encrypted output; round-trip it verbatim]\n")
            else:
                print(f"\n[advisor error: {content.error_code}; executor continues]\n")


def print_usage(summary, label: str, rates) -> None:
    print(f"\n{RULE}\nUsage breakdown: {label}\n{RULE}")
    header = f"{'iteration':<18}{'model':<24}{'input':>9}{'cache':>9}{'output':>9}"
    print(header)
    for i, row in enumerate(summary.rows, 1):
        kind = "executor" if row.kind == "message" else "advisor"
        print(
            f"{i:>2} {kind:<15}{row.model:<24}{row.input_tokens:>9}"
            f"{row.cache_read:>9}{row.output_tokens:>9}"
        )
    print(
        f"\nExecutor output tokens: {summary.executor_output}   "
        f"Advisor output tokens: {summary.advisor_output}   "
        f"Advisor calls: {summary.advisor_calls}"
    )
    cost = estimate_cost(summary, rates[0], rates[1]) if rates else None
    if cost is not None:
        print(f"Estimated cost at supplied rates: ${cost:.4f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Advisor tool demo (beta)")
    parser.add_argument("-q", "--query", default=DEFAULT_TASK, help="Task prompt")
    parser.add_argument("--executor", default=DEFAULT_EXECUTOR)
    parser.add_argument("--advisor", default=DEFAULT_ADVISOR)
    parser.add_argument(
        "--advisor-max-tokens",
        type=int,
        default=2048,
        help="Hard per-call cap on advisor output (min 1024, 0 disables)",
    )
    parser.add_argument(
        "--max-uses", type=int, default=3, help="Per-request advisor call cap"
    )
    parser.add_argument(
        "--brevity",
        action="store_true",
        help="Prefix the soft advisor-brevity line to the prompt",
    )
    parser.add_argument(
        "--caching",
        choices=["5m", "1h"],
        default=None,
        help="Advisor-side prompt caching TTL (breaks even at ~3 calls)",
    )
    parser.add_argument(
        "--no-system",
        action="store_true",
        help="Skip the suggested timing system prompt",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Also run executor-alone and report both usage breakdowns",
    )
    parser.add_argument(
        "--rates",
        nargs=4,
        type=float,
        metavar=("EXEC_IN", "EXEC_OUT", "ADV_IN", "ADV_OUT"),
        default=None,
        help="Optional $/MTok rates for a cost estimate; check current pricing",
    )
    args = parser.parse_args()

    client = get_client()
    rates = None
    if args.rates:
        rates = ((args.rates[0], args.rates[1]), (args.rates[2], args.rates[3]))

    prompt = with_brevity_hint(args.query) if args.brevity else args.query
    system = None if args.no_system else SUGGESTED_SYSTEM_PROMPT
    tool = make_advisor_tool(
        model=args.advisor,
        max_uses=args.max_uses,
        max_tokens=args.advisor_max_tokens or None,
        caching_ttl=args.caching,
    )

    if args.compare:
        print(f"{RULE}\nBaseline: {args.executor} alone\n{RULE}")
        baseline = run_turn(
            client,
            [{"role": "user", "content": args.query}],
            executor=args.executor,
        )
        print(final_text(baseline)[:1200])
        base_usage = summarize_usage(baseline, args.executor)
        print_usage(base_usage, f"{args.executor} alone", rates)

    print(f"\n{RULE}\nAdvised: {args.executor} + {args.advisor} advisor\n{RULE}")
    response = run_turn(
        client,
        [{"role": "user", "content": prompt}],
        executor=args.executor,
        tools=[tool],
        system=system,
    )
    print_transcript(response)

    events = extract_advisor_events(response)
    errors = [e for e in events if e.kind == "error"]
    if errors:
        codes = ", ".join(e.error_code for e in errors)
        print(f"Advisor errors encountered (executor continued): {codes}")

    usage = summarize_usage(response, args.executor)
    print_usage(usage, f"{args.executor} + {args.advisor}", rates)
    return 0


if __name__ == "__main__":
    sys.exit(main())
