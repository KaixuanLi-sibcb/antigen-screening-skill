#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.uniprot_parser import load_uniprot_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a UniProt-like fixture into normalized JSON")
    parser.add_argument("--input", required=True, type=Path, help="Input UniProt-like JSON fixture")
    parser.add_argument("--output", required=True, type=Path, help="Output normalized JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    record = load_uniprot_json(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "ok", "output": str(args.output), "gene_symbol": record["gene_symbol"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
