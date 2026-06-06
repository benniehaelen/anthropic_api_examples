"""
Run a code-execution request from the command line.

Claude writes and runs code in Anthropic's sandbox to satisfy your prompt; this prints the
interleaved transcript (narrative, code run, output) and downloads any files it created.

Usage (from the repo root):

    .venv\\Scripts\\python.exe code_execution/run_code.py -p "Plot y = x^2 for x in 0..10 and save plot.png"
    .venv\\Scripts\\python.exe code_execution/run_code.py -p "Clean and summarize this data" -f data.csv
    .venv\\Scripts\\python.exe code_execution/run_code.py -p "Profile this CSV" --sample

Requires ANTHROPIC_API_KEY (env var or a .env file at the repo root).
"""

import argparse
import os
import sys
import tempfile

from anthropic import Anthropic
from dotenv import load_dotenv

from _code_execution import (
    download_created_files,
    run_analysis,
    show_response,
    upload_file,
    write_sample_csv,
)


def main():
    parser = argparse.ArgumentParser(description="Have Claude write and run code in the sandbox.")
    parser.add_argument("--prompt", "-p", required=True, help="what Claude should do")
    parser.add_argument("--file", "-f", help="optional data file to upload for the sandbox to use")
    parser.add_argument("--sample", action="store_true", help="upload the built-in messy sales CSV")
    parser.add_argument("--out-dir", default=".", help="where to save files Claude creates (default: cwd)")
    parser.add_argument("--max-tokens", type=int, default=4096)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    load_dotenv()
    client = Anthropic()  # raises a clear error if ANTHROPIC_API_KEY is missing

    file_id = None
    if args.sample:
        path = write_sample_csv(os.path.join(tempfile.gettempdir(), "sample_sales.csv"))
        print(f"Uploading built-in sample: {path}")
        file_id = upload_file(client, path).id
    elif args.file:
        if not os.path.isfile(args.file):
            sys.exit(f"error: no such file: {args.file}")
        print(f"Uploading {args.file} …")
        file_id = upload_file(client, args.file).id

    print("Running in the sandbox …\n")
    response = run_analysis(client, args.prompt, file_id=file_id, max_tokens=args.max_tokens)
    show_response(response)

    saved = download_created_files(client, response, dest_dir=args.out_dir)
    if saved:
        print("\n── files created ──")
        for path in saved:
            print(f"  {path} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
