#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.io import CANDIDATE_OUTPUT_COLUMNS, RISK_COLUMNS, normalize_candidate_rows, read_tsv, write_jsonl, write_tsv
from antigen_screening.evidence_conflict import write_conflict_report
from antigen_screening.scoring import evaluate_candidate
from antigen_screening.uniprot_parser import fixture_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate and score antigen candidates from local UniProt-like fixtures")
    parser.add_argument("--input", required=True, type=Path, help="Candidate TSV")
    parser.add_argument("--fixtures-dir", required=True, type=Path, help="Directory containing UniProt-like fixtures")
    parser.add_argument("--outdir", required=True, type=Path, help="Output directory")
    parser.add_argument("--offline", action="store_true", help="Require fixture/local mode; do not use network")
    parser.add_argument("--species", default="human", help="Default species")
    parser.add_argument("--ecd-identity-threshold", type=float, default=0.70, help="Human-mouse ECD identity threshold")
    parser.add_argument("--mouse-model", action="store_true", help="Enable human-mouse ECD transferability gate")
    parser.add_argument("--dry-run", action="store_true", help="Show planned outputs without writing screening files")
    args = parser.parse_args()

    if not args.offline:
        print("Live mode is not implemented for scoring; use --offline with fixtures.", file=sys.stderr)
        return 2

    rows = normalize_candidate_rows(read_tsv(args.input), args.species)
    index = fixture_index(args.fixtures_dir)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "candidates": [row["gene_symbol"] for row in rows],
                    "fixtures": sorted(index.keys()),
                    "outdir": str(args.outdir),
                },
                indent=2,
            )
        )
        return 0

    screening_rows = []
    evidence_rows = []
    risk_rows = []
    for row in rows:
        record = index.get(row["gene_symbol"].upper())
        screening, evidence, risks = evaluate_candidate(row, record, args.ecd_identity_threshold, args.mouse_model)
        screening_rows.append(screening)
        evidence_rows.extend(evidence)
        risk_rows.extend(risks)

    args.outdir.mkdir(parents=True, exist_ok=True)
    write_tsv(args.outdir / "antigen_screening_table.tsv", screening_rows, CANDIDATE_OUTPUT_COLUMNS)
    write_jsonl(args.outdir / "evidence_records.jsonl", evidence_rows)
    write_conflict_report(evidence_rows, args.outdir)
    write_tsv(args.outdir / "risk_flags.tsv", risk_rows, RISK_COLUMNS)
    print(
        json.dumps(
            {
                "status": "ok",
                "offline": True,
                "rows": len(screening_rows),
                "outputs": [
                    str(args.outdir / "antigen_screening_table.tsv"),
                    str(args.outdir / "evidence_records.jsonl"),
                    str(args.outdir / "evidence_conflicts.tsv"),
                    str(args.outdir / "evidence_conflict_summary.json"),
                    str(args.outdir / "risk_flags.tsv"),
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
