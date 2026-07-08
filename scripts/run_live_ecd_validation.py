#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.io import write_jsonl, write_tsv
from antigen_screening.live_ecd import validate_ecd_identity
from antigen_screening.live_ensembl import ensembl_evidence_records, load_ensembl_source
from antigen_screening.live_uniprot import load_uniprot_source, normalize_live_uniprot, uniprot_evidence_records


CONFLICT_COLUMNS = [
    "candidate_id",
    "gene_symbol",
    "conflict_type",
    "local_value",
    "computed_value",
    "difference",
    "tolerance",
    "failure_mode",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate human/mouse ECD identity with UniProt and Ensembl evidence")
    parser.add_argument("--gene-symbol", required=True, help="Human gene symbol")
    parser.add_argument("--accession", default="", help="Human UniProt accession")
    parser.add_argument("--species", default="human", help="Source species; default human")
    parser.add_argument("--target-species", default="mouse", help="Target species; default mouse")
    parser.add_argument("--target-taxon", default="10090", help="Target taxon; default mouse 10090")
    parser.add_argument("--outdir", required=True, type=Path, help="Output directory")
    parser.add_argument("--human-uniprot-fixture", type=Path, help="UniProt-like human fixture JSON")
    parser.add_argument("--ensembl-fixture", type=Path, help="Ensembl-like homology fixture JSON")
    parser.add_argument("--local-ecd-identity", default="", help="Local ECD identity value for comparison")
    parser.add_argument("--identity-conflict-tolerance", type=float, default=0.05, help="Allowed absolute identity difference")
    parser.add_argument("--no-network", action="store_true", help="Do not call live APIs")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON outputs")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []

    uniprot_kind, uniprot_raw, uniprot_metadata = load_uniprot_source(
        accession=args.accession,
        gene_symbol=args.gene_symbol,
        species=args.species,
        offline_fixture=args.human_uniprot_fixture,
        no_network=args.no_network,
        timeout=args.timeout,
    )
    human_record = None
    if uniprot_raw is not None and uniprot_kind in {"live", "fixture"}:
        human_record = normalize_live_uniprot(uniprot_raw, str(args.human_uniprot_fixture or "uniprot_live"))
    records.extend(
        uniprot_evidence_records(
            normalized=human_record,
            raw=uniprot_raw,
            kind=uniprot_kind,
            metadata=uniprot_metadata,
            candidate_id=args.accession or args.gene_symbol,
            gene_symbol=args.gene_symbol,
            species=args.species,
            query={"accession": args.accession, "gene_symbol": args.gene_symbol, "species": args.species},
        )
    )

    ensembl_kind, ensembl_raw, ensembl_metadata = load_ensembl_source(
        gene_symbol=args.gene_symbol,
        species=args.species,
        target_species=args.target_species,
        target_taxon=args.target_taxon,
        offline_fixture=args.ensembl_fixture,
        no_network=args.no_network,
        timeout=args.timeout,
    )
    ensembl_records, orthologs = ensembl_evidence_records(
        raw=ensembl_raw,
        kind=ensembl_kind,
        metadata=ensembl_metadata,
        candidate_id=args.accession or args.gene_symbol,
        gene_symbol=args.gene_symbol,
        species=args.species,
        target_species=args.target_species,
        target_taxon=args.target_taxon,
        query={
            "gene_symbol": args.gene_symbol,
            "species": args.species,
            "target_species": args.target_species,
            "target_taxon": args.target_taxon,
        },
    )
    records.extend(ensembl_records)

    source_kind = "live" if uniprot_kind == "live" and ensembl_kind == "live" else "fixture"
    summary, ecd_records, conflicts = validate_ecd_identity(
        human_record=human_record,
        ortholog=orthologs[0] if len(orthologs) == 1 else None,
        candidate_id=args.accession or args.gene_symbol,
        gene_symbol=args.gene_symbol,
        species=args.species,
        uniprot_accession=(human_record or {}).get("accession", args.accession),
        local_ecd_identity=args.local_ecd_identity,
        tolerance=args.identity_conflict_tolerance,
        source_kind=source_kind,
    )
    records.extend(ecd_records)

    write_jsonl(args.outdir / "live_ecd_evidence_records.jsonl", records)
    write_tsv(args.outdir / "live_ecd_conflicts.tsv", conflicts, CONFLICT_COLUMNS)
    (args.outdir / "live_ecd_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    status = "pass" if summary["status"] in {"pass", "missing"} else "conflict" if summary["status"] == "conflict" else "fail"
    cli_summary = {
        "status": status,
        "uniprot_mode": uniprot_kind,
        "ensembl_mode": ensembl_kind,
        "outdir": str(args.outdir),
        "evidence_records": len(records),
        "conflict_count": len(conflicts),
        "outputs": {
            "evidence_records": str(args.outdir / "live_ecd_evidence_records.jsonl"),
            "conflicts": str(args.outdir / "live_ecd_conflicts.tsv"),
            "summary": str(args.outdir / "live_ecd_summary.json"),
        },
    }
    print(json.dumps(cli_summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if status in {"pass", "conflict"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
