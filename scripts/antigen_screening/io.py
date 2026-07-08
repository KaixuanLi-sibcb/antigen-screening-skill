from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping


CANDIDATE_OUTPUT_COLUMNS = [
    "candidate_id",
    "input_name",
    "species",
    "gene_symbol",
    "modality",
    "disease_context",
    "user_evidence",
    "uniprot_accession",
    "protein_name",
    "antigen_accessibility",
    "accessibility_gate",
    "accessibility_evidence_state",
    "topology_evidence",
    "ecd_region",
    "ecd_length",
    "ecd_evidence_state",
    "ecd_boundary_confidence",
    "ecd_notes",
    "isoform_risk",
    "disease_relevance_gate",
    "disease_evidence_state",
    "normal_tissue_risk",
    "normal_tissue_risk_evidence_state",
    "mouse_model_transferability_gate",
    "human_mouse_ecd_identity",
    "ecd_identity_threshold",
    "orthology_evidence_state",
    "constructability_gate",
    "constructability_class",
    "modality_fit",
    "modality_gate",
    "modality_evidence_state",
    "known_evidence",
    "risk_flags",
    "tie_break_score",
    "priority_call",
    "decision_rationale",
    "missing_evidence",
]

RISK_COLUMNS = ["gene_symbol", "flag_type", "severity", "evidence", "action"]

CONSTRUCT_COLUMNS = [
    "gene_symbol",
    "modality",
    "accessibility_gate",
    "constructability_gate",
    "ecd_region",
    "ecd_length",
    "construct_recommendation",
    "construct_variant_1",
    "construct_variant_2",
    "include_signal_peptide",
    "remove_tm",
    "remove_cytoplasmic_tail",
    "tag_strategy",
    "display_strategy",
    "expression_system",
    "qc_plan",
    "construct_risks",
    "evidence_state",
    "stop_condition",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def write_tsv(path: Path, rows: Iterable[Mapping[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if row.get(key) is None else row.get(key) for key in columns})


def write_jsonl(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")


def read_required_columns(schema_tsv: Path) -> dict[str, list[str]]:
    rows = read_tsv(schema_tsv)
    out: dict[str, list[str]] = {}
    if "file" in rows[0] and "column" in rows[0]:
        for row in rows:
            out.setdefault(row["file"], []).append(row["column"])
        return out
    if "column" in rows[0]:
        out[str(schema_tsv.name)] = [row["column"] for row in rows if row.get("required", "yes") == "yes"]
    return out


def normalize_candidate_rows(rows: list[dict[str, str]], default_species: str = "human") -> list[dict[str, str]]:
    normalized = []
    for index, row in enumerate(rows, start=1):
        gene_symbol = (row.get("gene_symbol") or row.get("input_name") or row.get("target") or "").strip()
        if not gene_symbol:
            raise ValueError(f"Input row {index} has no gene_symbol/input_name")
        species = (row.get("species") or default_species or "human").strip().lower()
        modality = (row.get("modality") or "unknown").strip().lower()
        normalized.append(
            {
                **row,
                "candidate_id": row.get("candidate_id") or f"CAND{index:04d}",
                "input_name": row.get("input_name") or gene_symbol,
                "gene_symbol": gene_symbol.upper(),
                "species": species,
                "modality": modality,
                "disease_context": row.get("disease_context", ""),
                "user_evidence": row.get("user_evidence", ""),
            }
        )
    return normalized
