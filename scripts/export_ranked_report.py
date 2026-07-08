#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.report_priority import run_report_priority


def main() -> int:
    parser = argparse.ArgumentParser(description="Export report-ready antigen priority ranking")
    parser.add_argument("--screening-table", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--readiness-table", type=Path)
    parser.add_argument("--normal-tissue-risk", type=Path)
    parser.add_argument("--construct-plan", type=Path)
    parser.add_argument("--screening-strategy", type=Path)
    parser.add_argument("--coverage-diagnostics", type=Path)
    parser.add_argument("--join-evidence", type=Path)
    parser.add_argument(
        "--identity-preference",
        choices=["low_for_antibody_screening", "high_for_mouse_model_transferability"],
        default="low_for_antibody_screening",
        help="How to interpret human-mouse ECD identity for report ranking",
    )
    parser.add_argument("--no-xlsx", action="store_true", help="Write TSV/JSON/Markdown only")
    args = parser.parse_args()

    try:
        summary = run_report_priority(
            screening_table=args.screening_table,
            readiness_table=args.readiness_table,
            normal_tissue_risk=args.normal_tissue_risk,
            construct_plan=args.construct_plan,
            screening_strategy=args.screening_strategy,
            coverage_diagnostics=args.coverage_diagnostics,
            join_evidence=args.join_evidence,
            outdir=args.outdir,
            identity_preference=args.identity_preference,
            write_xlsx=not args.no_xlsx,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Report priority export failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
