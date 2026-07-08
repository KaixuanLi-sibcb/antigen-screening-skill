#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.hpa_adapter import run_hpa_normal_tissue_risk


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fixture-backed HPA normal tissue risk triage")
    parser.add_argument("--input", required=True, type=Path, help="Candidate or antigen screening TSV")
    parser.add_argument("--outdir", required=True, type=Path, help="Output directory")
    parser.add_argument("--fixtures-dir", type=Path, help="Directory with HPA-like fixture JSON files")
    parser.add_argument("--offline", action="store_true", help="Use fixture mode and do not call HPA live endpoint")
    parser.add_argument("--allow-live", action="store_true", help="Allow live HPA lookup if fixture is missing")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    args = parser.parse_args()

    if not args.input.exists():
        print(json.dumps({"status": "fail", "error": f"input not found: {args.input}"}, indent=2), file=sys.stderr)
        return 2
    offline = args.offline or not args.allow_live
    try:
        summary = run_hpa_normal_tissue_risk(
            input_path=args.input,
            outdir=args.outdir,
            fixtures_dir=args.fixtures_dir,
            offline=offline,
            timeout=args.timeout,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "fail", "error": f"{type(exc).__name__}: {exc}"}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
