#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.construct import construct_plan_for
from antigen_screening.io import CONSTRUCT_COLUMNS, read_tsv, write_tsv
from antigen_screening.report import write_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Create construct plan from antigen screening table")
    parser.add_argument("--input", required=True, type=Path, help="antigen_screening_table.tsv")
    parser.add_argument("--outdir", required=True, type=Path, help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Show planned output path without writing")
    args = parser.parse_args()

    rows = read_tsv(args.input)
    if args.dry_run:
        print(json.dumps({"status": "dry_run", "rows": len(rows), "outdir": str(args.outdir)}, indent=2))
        return 0

    plans = [construct_plan_for(row) for row in rows]
    args.outdir.mkdir(parents=True, exist_ok=True)
    write_tsv(args.outdir / "construct_plan.tsv", plans, CONSTRUCT_COLUMNS)
    write_report(args.outdir / "report.md", rows, plans, offline=True)
    print(
        json.dumps(
            {
                "status": "ok",
                "rows": len(plans),
                "outputs": [str(args.outdir / "construct_plan.tsv"), str(args.outdir / "report.md")],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
