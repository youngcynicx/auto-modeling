#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a CadQuery model script and list generated CAD outputs.")
    parser.add_argument("script", type=Path, help="Path to a Python CadQuery model script")
    parser.add_argument("--python", default=sys.executable, help="Python executable to use")
    args = parser.parse_args()

    script = args.script.resolve()
    if not script.exists():
        print(f"Script not found: {script}", file=sys.stderr)
        return 2

    before = snapshot(script.parent)
    subprocess.run([args.python, str(script)], cwd=str(script.parent), check=True)
    after = snapshot(script.parent)

    generated = sorted(after - before)
    if generated:
        print("Generated files:")
        for path in generated:
            print(f"- {path}")
    else:
        print("No new STEP/STL/SVG files detected; check script output paths.")
    return 0


def snapshot(root: Path) -> set[Path]:
    exts = {".step", ".stp", ".stl", ".svg", ".fcstd"}
    return {p.resolve() for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts}


if __name__ == "__main__":
    raise SystemExit(main())
