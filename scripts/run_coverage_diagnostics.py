#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.coverage_diagnostics import run_coverage_diagnostics


def _load_json_mapping(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"mapping file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run coverage diagnostics and ID rescue for antigen-screening outputs")
    parser.add_argument("--input", required=True, type=Path, help="antigen_screening_table.tsv or compatible candidate table")
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--evidence-records", type=Path)
    parser.add_argument("--normal-tissue-risk", type=Path)
    parser.add_argument("--alias-map-json", type=Path)
    parser.add_argument("--uniprot-map-json", type=Path)
    parser.add_argument("--ensembl-map-json", type=Path)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"input not found: {args.input}", file=sys.stderr)
        return 2
    try:
        summary = run_coverage_diagnostics(
            screening_table=args.input,
            outdir=args.outdir,
            evidence_records_path=args.evidence_records,
            normal_tissue_risk_path=args.normal_tissue_risk,
            alias_map=_load_json_mapping(args.alias_map_json),
            uniprot_map=_load_json_mapping(args.uniprot_map_json),
            ensembl_map=_load_json_mapping(args.ensembl_map_json),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"coverage diagnostics failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
