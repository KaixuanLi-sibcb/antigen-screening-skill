#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from antigen_screening.io import normalize_candidate_rows, read_tsv, write_jsonl


UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"
UNIPROT_ENTRY = "https://rest.uniprot.org/uniprotkb/{accession}.json"

SPECIES_TO_TAXON = {
    "human": 9606,
    "homo sapiens": 9606,
    "mouse": 10090,
    "mus musculus": 10090,
}


def http_json(url: str, timeout: int) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "antigen-screening/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def search_accession(symbol: str, taxon_id: int, timeout: int) -> str:
    query = f"(gene_exact:{symbol}) AND (organism_id:{taxon_id}) AND (reviewed:true)"
    params = {"query": query, "format": "json", "size": "1"}
    data = http_json(UNIPROT_SEARCH + "?" + urllib.parse.urlencode(params), timeout)
    results = data.get("results") or []
    if results:
        return str(results[0].get("primaryAccession") or "")
    return ""


def fetch_entry(accession: str, timeout: int) -> dict:
    return http_json(UNIPROT_ENTRY.format(accession=urllib.parse.quote(accession)), timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch UniProt records for antigen candidates")
    parser.add_argument("--input", required=True, type=Path, help="Candidate TSV")
    parser.add_argument("--output", required=True, type=Path, help="Output JSONL")
    parser.add_argument("--species", default="human", help="Default species for rows without species")
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay between requests")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Print planned queries without network calls")
    args = parser.parse_args()

    rows = normalize_candidate_rows(read_tsv(args.input), args.species)
    out_rows = []
    for row in rows:
        taxon = SPECIES_TO_TAXON.get(row["species"].lower(), 9606)
        accession = row.get("uniprot_accession") or ""
        if args.dry_run:
            out_rows.append(
                {
                    "input": row,
                    "status": "dry_run",
                    "query": {"gene_symbol": row["gene_symbol"], "taxon_id": taxon, "accession": accession},
                    "uniprot_record": None,
                }
            )
            continue
        status = "ok"
        error = ""
        record = None
        try:
            if not accession:
                accession = search_accession(row["gene_symbol"], taxon, args.timeout)
            if accession:
                record = fetch_entry(accession, args.timeout)
            else:
                status = "not_found"
                error = "no reviewed UniProt accession found"
        except Exception as exc:  # noqa: BLE001
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
        out_rows.append({"input": row, "status": status, "error": error, "accession": accession, "uniprot_record": record})
        time.sleep(args.sleep)

    write_jsonl(args.output, out_rows)
    print(json.dumps({"status": "ok", "output": str(args.output), "rows": len(out_rows), "dry_run": args.dry_run}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
