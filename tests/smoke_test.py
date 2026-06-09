"""
Repo smoke test — fast, offline, no API calls (and no API key required).

Catches the ways these examples silently rot:
  1. Every .py file compiles.
  2. Every shared module (`_*.py`, plus mcp/server.py) imports cleanly — this catches missing
     dependencies and import-time errors that py_compile alone misses.
  3. Every notebook (.ipynb) is well-formed JSON with cells.

Run locally:  .venv\\Scripts\\python.exe tests/smoke_test.py
Exits non-zero on any failure (used by CI).
"""

import importlib.util
import json
import os
import py_compile
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".venv", ".git", "__pycache__", ".ipynb_checkpoints", ".github"}

failures = []


def walk(ext):
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(ext):
                yield os.path.join(dirpath, name)


# 1. Compile every .py
py_files = sorted(walk(".py"))
for path in py_files:
    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as exc:
        failures.append(f"compile: {os.path.relpath(path, ROOT)}: {exc.msg}")
print(f"compiled {len(py_files)} .py files")


# 2. Import each shared module (underscore-prefixed) + mcp/server.py.
#    These define helpers and must not touch the network or need a key at import time.
def is_shared(path):
    base = os.path.basename(path)
    return base.startswith("_") and base != "__init__.py" or base == "server.py"


shared = [p for p in py_files if is_shared(p) and "tests" not in os.path.relpath(p, ROOT).split(os.sep)]
imported = 0
for path in shared:
    folder = os.path.dirname(path)
    modname = "smoke_" + os.path.splitext(os.path.basename(path))[0] + "_" + os.path.basename(folder)
    sys.path.insert(0, folder)
    try:
        spec = importlib.util.spec_from_file_location(modname, path)
        module = importlib.util.module_from_spec(spec)
        # Register before exec: dataclasses (and other machinery) look the module up in
        # sys.modules by name during class creation.
        sys.modules[modname] = module
        spec.loader.exec_module(module)
        imported += 1
    except Exception as exc:  # noqa: BLE001 — report any import failure
        failures.append(f"import: {os.path.relpath(path, ROOT)}: {type(exc).__name__}: {exc}")
    finally:
        sys.modules.pop(modname, None)
        if sys.path and sys.path[0] == folder:
            sys.path.pop(0)
print(f"imported {imported}/{len(shared)} shared modules")


# 3. Validate every notebook
nbs = sorted(walk(".ipynb"))
for path in nbs:
    rel = os.path.relpath(path, ROOT)
    try:
        with open(path, encoding="utf-8") as handle:
            nb = json.load(handle)
        cells = nb.get("cells")
        if not isinstance(cells, list) or not cells:
            failures.append(f"notebook: {rel}: no cells")
            continue
        for i, cell in enumerate(cells):
            if "cell_type" not in cell or "source" not in cell:
                failures.append(f"notebook: {rel}: cell {i} missing cell_type/source")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"notebook: {rel}: {type(exc).__name__}: {exc}")
print(f"validated {len(nbs)} notebooks")


# Summary
print("-" * 50)
if failures:
    print(f"FAILED ({len(failures)}):")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("OK - all smoke checks passed")
