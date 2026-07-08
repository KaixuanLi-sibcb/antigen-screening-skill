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
from antigen_screening.live_uniprot import load_uniprot_source, normalize_live_uniprot, uniprot_evidence_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch or parse UniProt live/fixture evidence for ECD validation")
    parser.add_argument("--accession", default="", help="UniProt accession")
    parser.add_argument("--gene-symbol", default="", help="Gene symbol fallback")
    parser.add_argument("--species", default="human", help="Species name; default human")
    parser.add_argument("--outdir", required=True, type=Path, help="Output directory")
    parser.add_argument("--offline-fixture", type=Path, help="UniProt-like fixture JSON")
    parser.add_argument("--no-network", action="store_true", help="Do not call UniProt live API")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print normalized JSON")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    cache_dir = args.outdir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    kind, raw, metadata = load_uniprot_source(
        accession=args.accession,
        gene_symbol=args.gene_symbol,
        species=args.species,
        offline_fixture=args.offline_fixture,
        no_network=args.no_network,
        timeout=args.timeout,
    )
    normalized = None
    status = "pass"
    if raw is not None and kind in {"live", "fixture"}:
        try:
            raw_path = cache_dir / f"uniprot_{args.accession or args.gene_symbol or 'record'}.json"
            raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            normalized = normalize_live_uniprot(raw, str(raw_path if kind == "live" else args.offline_fixture or raw_path))
        except Exception as exc:  # noqa: BLE001
            kind = "error"
            metadata = {"error": f"{type(exc).__name__}: {exc}", "source_name": metadata.get("source_name", "uniprot_live")}
            status = "fail"
    elif kind == "error":
        status = "fail"

    query = {"accession": args.accession, "gene_symbol": args.gene_symbol, "species": args.species, "no_network": str(args.no_network)}
    records = uniprot_evidence_records(
        normalized=normalized,
        raw=raw,
        kind=kind,
        metadata=metadata,
        candidate_id=args.accession or args.gene_symbol,
        gene_symbol=args.gene_symbol or (normalized or {}).get("gene_symbol", ""),
        species=args.species,
        query=query,
    )
    write_jsonl(args.outdir / "uniprot_evidence_records.jsonl", records)
    if normalized is not None:
        (args.outdir / "uniprot_normalized.json").write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    summary = {
        "status": status if status == "fail" else ("pass" if kind in {"live", "fixture", "missing"} else "fail"),
        "mode": kind,
        "accession": (normalized or {}).get("accession", args.accession),
        "gene_symbol": (normalized or {}).get("gene_symbol", args.gene_symbol),
        "outdir": str(args.outdir),
        "evidence_records": len(records),
        "error": metadata.get("error", ""),
        "outputs": {
            "evidence_records": str(args.outdir / "uniprot_evidence_records.jsonl"),
            "normalized": str(args.outdir / "uniprot_normalized.json") if normalized is not None else "",
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
