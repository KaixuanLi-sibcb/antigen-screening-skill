#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.io import write_jsonl
from antigen_screening.live_ensembl import ensembl_evidence_records, load_ensembl_source


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch or parse Ensembl human-mouse orthology evidence")
    parser.add_argument("--gene-symbol", required=True, help="Source gene symbol")
    parser.add_argument("--species", default="human", help="Source species accepted by Ensembl REST; default human")
    parser.add_argument("--target-species", default="mouse", help="Target species accepted by Ensembl REST; default mouse")
    parser.add_argument("--target-taxon", default="10090", help="Target taxon id; default 10090 for mouse")
    parser.add_argument("--outdir", required=True, type=Path, help="Output directory")
    parser.add_argument("--offline-fixture", type=Path, help="Ensembl-like homology fixture JSON")
    parser.add_argument("--no-network", action="store_true", help="Do not call Ensembl live API")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print raw orthology JSON")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    cache_dir = args.outdir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    kind, raw, metadata = load_ensembl_source(
        gene_symbol=args.gene_symbol,
        species=args.species,
        target_species=args.target_species,
        target_taxon=args.target_taxon,
        offline_fixture=args.offline_fixture,
        no_network=args.no_network,
        timeout=args.timeout,
    )
    status = "pass"
    if kind == "error":
        status = "fail"
    if raw is not None and kind in {"live", "fixture"}:
        raw_path = cache_dir / f"ensembl_{args.gene_symbol}_{args.species}_to_{args.target_species}.json"
        raw_path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (args.outdir / "ensembl_orthology.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    query = {
        "gene_symbol": args.gene_symbol,
        "species": args.species,
        "target_species": args.target_species,
        "target_taxon": args.target_taxon,
        "no_network": str(args.no_network),
    }
    records, orthologs = ensembl_evidence_records(
        raw=raw,
        kind=kind,
        metadata=metadata,
        candidate_id=args.gene_symbol,
        gene_symbol=args.gene_symbol,
        species=args.species,
        target_species=args.target_species,
        target_taxon=args.target_taxon,
        query=query,
    )
    write_jsonl(args.outdir / "ensembl_evidence_records.jsonl", records)

    summary = {
        "status": status if status == "fail" else ("pass" if kind in {"live", "fixture", "missing"} else "fail"),
        "mode": kind,
        "gene_symbol": args.gene_symbol,
        "species": args.species,
        "target_species": args.target_species,
        "ortholog_count": len(orthologs),
        "outdir": str(args.outdir),
        "evidence_records": len(records),
        "error": metadata.get("error", ""),
        "outputs": {
            "evidence_records": str(args.outdir / "ensembl_evidence_records.jsonl"),
            "orthology": str(args.outdir / "ensembl_orthology.json") if raw is not None else "",
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
