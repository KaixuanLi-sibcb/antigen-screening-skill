#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.screening_strategy import run_screening_strategy


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan antibody screening antigen strategy from antigen readiness output")
    parser.add_argument("--input", required=True, type=Path, help="Antigen readiness TSV")
    parser.add_argument("--outdir", required=True, type=Path, help="Output directory")
    args = parser.parse_args()

    if not args.input.exists():
        print(json.dumps({"status": "fail", "error": f"input not found: {args.input}"}, indent=2), file=sys.stderr)
        return 2
    try:
        summary = run_screening_strategy(args.input, args.outdir)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "fail", "error": f"{type(exc).__name__}: {exc}"}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
