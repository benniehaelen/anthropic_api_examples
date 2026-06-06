"""
Search a folder of documents from the command line.

Embeds the documents with Voyage, retrieves the passages most relevant to your query, and has
Claude answer from them with citations. Prints the answer and the ranked passages; optionally
writes the cited result to an HTML file.

Usage (from the repo root):

    .venv\\Scripts\\python.exe documents/run_search.py <files-or-folder> --query "your question"
    .venv\\Scripts\\python.exe documents/run_search.py ./docs --query "..." --k 8 --out answer.html

Requires ANTHROPIC_API_KEY and VOYAGE_API_KEY (env vars or a .env file at the repo root).
"""

import argparse
import os
import sys

from anthropic import Anthropic
from dotenv import load_dotenv

from _documents import (
    SUPPORTED_EXTS,
    answer,
    answer_text,
    build_library,
    render_html,
    retrieve,
)


def collect_files(paths):
    """Expand paths (files or directories) into [(filename, bytes)] for supported types."""
    files = []
    for path in paths:
        if os.path.isdir(path):
            for entry in sorted(os.listdir(path)):
                full = os.path.join(path, entry)
                if os.path.isfile(full) and entry.lower().endswith(SUPPORTED_EXTS):
                    with open(full, "rb") as handle:
                        files.append((entry, handle.read()))
        elif os.path.isfile(path):
            if not path.lower().endswith(SUPPORTED_EXTS):
                sys.exit(f"error: unsupported file type: {path}. Supported: {', '.join(SUPPORTED_EXTS)}")
            with open(path, "rb") as handle:
                files.append((os.path.basename(path), handle.read()))
        else:
            sys.exit(f"error: no such file or directory: {path}")
    return files


def main():
    parser = argparse.ArgumentParser(description="Search documents with Voyage retrieval + Claude citations.")
    parser.add_argument("paths", nargs="+", help="document files and/or directories to search")
    parser.add_argument("--query", "-q", required=True, help="the search query / question")
    parser.add_argument("--k", type=int, default=5, help="number of passages to retrieve (default 5)")
    parser.add_argument("--out", help="optional path to write the cited answer as an HTML file")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    missing = [k for k in ("ANTHROPIC_API_KEY", "VOYAGE_API_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(f"error: missing {' and '.join(missing)} (set env var or add to .env)")

    files = collect_files(args.paths)
    if not files:
        sys.exit("error: no supported documents found.")

    print(f"Indexing {len(files)} document(s): {', '.join(n for n, _ in files)} …")
    chunks, skipped = build_library(files)
    if skipped:
        print(f"  skipped (no extractable text): {', '.join(skipped)}")
    if not chunks:
        sys.exit("error: no searchable text extracted.")
    print(f"  {len(chunks)} chunks embedded.\n")

    retrieved = retrieve(args.query, chunks, k=args.k)
    content = answer(Anthropic(), args.query, retrieved)

    print("Answer")
    print("-" * 60)
    print(answer_text(content))

    print("\nRetrieved passages (ranked)")
    print("-" * 60)
    for i, passage in enumerate(retrieved):
        print(f"#{i + 1}  [{passage['source']}]  cosine {passage['score']:.3f}")
        print(f"    {passage['text'][:140]}{'…' if len(passage['text']) > 140 else ''}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(render_html(args.query, content, retrieved))
        print(f"\nWrote cited HTML to {args.out}")


if __name__ == "__main__":
    main()
