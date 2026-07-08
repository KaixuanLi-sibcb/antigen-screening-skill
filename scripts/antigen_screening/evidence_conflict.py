from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .io import write_tsv


CONFLICT_COLUMNS = [
    "candidate_id",
    "gene_symbol",
    "evidence_type",
    "conflict_status",
    "values",
    "sources",
    "record_count",
    "failure_mode",
]


def _usable_value(record: dict[str, str]) -> str:
    if record.get("evidence_status") in {"missing", "not_applicable", "error"}:
        return ""
    return (record.get("normalized_value") or record.get("evidence_value") or "").strip()


def detect_conflicts(records: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for record in records:
        groups[(record.get("candidate_id", ""), record.get("evidence_type", ""))].append(record)

    conflicts: list[dict[str, str]] = []
    for (candidate_id, evidence_type), grouped in sorted(groups.items()):
        values = sorted({value for record in grouped if (value := _usable_value(record))})
        sources = sorted({record.get("source_name", "") for record in grouped if record.get("source_name", "")})
        if len(values) > 1:
            conflicts.append(
                {
                    "candidate_id": candidate_id,
                    "gene_symbol": grouped[0].get("gene_symbol", ""),
                    "evidence_type": evidence_type,
                    "conflict_status": "value_conflict",
                    "values": "|".join(values),
                    "sources": "|".join(sources),
                    "record_count": str(len(grouped)),
                    "failure_mode": "same candidate/evidence_type has multiple normalized values",
                }
            )
        elif len(sources) > 1 and any(record.get("source_name", "").startswith("future_live") for record in grouped):
            conflicts.append(
                {
                    "candidate_id": candidate_id,
                    "gene_symbol": grouped[0].get("gene_symbol", ""),
                    "evidence_type": evidence_type,
                    "conflict_status": "source_conflict",
                    "values": "|".join(values),
                    "sources": "|".join(sources),
                    "record_count": str(len(grouped)),
                    "failure_mode": "local or fixture evidence coexists with future live placeholder",
                }
            )
    return conflicts


def write_conflict_report(records: list[dict[str, str]], outdir: Path) -> dict[str, object]:
    outdir.mkdir(parents=True, exist_ok=True)
    conflicts = detect_conflicts(records)
    write_tsv(outdir / "evidence_conflicts.tsv", conflicts, CONFLICT_COLUMNS)
    summary: dict[str, object] = {
        "status": "pass" if not conflicts else "conflict",
        "records_checked": len(records),
        "conflict_count": len(conflicts),
        "conflict_status_counts": {},
    }
    counts: dict[str, int] = {}
    for row in conflicts:
        counts[row["conflict_status"]] = counts.get(row["conflict_status"], 0) + 1
    summary["conflict_status_counts"] = counts
    (outdir / "evidence_conflict_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
