from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .id_mapping import ID_MAPPING_RESCUE_COLUMNS, rescue_candidates
from .io import read_tsv, write_tsv


COVERAGE_DIAGNOSTICS_COLUMNS = [
    "candidate_id",
    "gene_symbol",
    "species",
    "input_identifier",
    "resolved_gene_symbol",
    "hgnc_status",
    "uniprot_accession",
    "uniprot_status",
    "ensembl_gene_id",
    "ensembl_status",
    "mouse_ortholog_symbol",
    "mouse_ortholog_status",
    "hpa_status",
    "gtex_status",
    "opentargets_status",
    "chembl_status",
    "clinicaltrials_status",
    "normal_tissue_status",
    "drug_evidence_status",
    "construct_status",
    "live_ecd_status",
    "evidence_status_overall",
    "missing_reason_primary",
    "missing_reason_secondary",
    "recommended_rescue_action",
    "confidence",
    "notes",
]

ADAPTER_READINESS_COLUMNS = [
    "adapter_name",
    "adapter_scope",
    "input_required",
    "current_status",
    "offline_fixture_available",
    "live_mode_available",
    "batch_mode_available",
    "ci_enabled",
    "privacy_risk",
    "next_required_work",
]

MISSING_REASONS = {
    "id_mapping_missing",
    "id_mapping_ambiguous",
    "source_not_configured",
    "adapter_not_implemented",
    "adapter_not_run",
    "source_record_missing",
    "source_field_missing",
    "query_error",
    "network_unavailable",
    "fixture_only",
    "not_applicable_to_modality",
    "conflicting_sources",
    "insufficient_topology",
    "insufficient_ecd_boundary",
    "insufficient_orthology",
    "private_source_absent",
    "coverage_pending",
    "unknown",
}

ADAPTER_STATUSES = {
    "implemented_fixture",
    "implemented_live_optional",
    "implemented_local_only",
    "adapter_not_implemented",
    "planned",
    "not_applicable",
    "deprecated",
}


def read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _nonempty(value: Any) -> bool:
    return str(value or "").strip() not in {"", "missing", "unknown", "not_available", "na", "NA"}


def _by_candidate(rows: list[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    out: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        key = str(row.get("candidate_id") or row.get("gene_symbol") or "")
        if key:
            out.setdefault(key, []).append(row)
    return out


def _row_by_candidate_or_symbol(rows: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        cid = str(row.get("candidate_id") or "")
        symbol = str(row.get("gene_symbol") or "")
        if cid:
            out[cid] = row
        if symbol:
            out.setdefault(symbol.upper(), row)
    return out


def adapter_readiness_matrix() -> list[dict[str, str]]:
    return [
        {
            "adapter_name": "uniprot",
            "adapter_scope": "accession, sequence, feature, topology lookup",
            "input_required": "gene_symbol or uniprot_accession",
            "current_status": "implemented_live_optional",
            "offline_fixture_available": "yes",
            "live_mode_available": "yes",
            "batch_mode_available": "no",
            "ci_enabled": "fixture_only",
            "privacy_risk": "low",
            "next_required_work": "batch cassette coverage and cache policy",
        },
        {
            "adapter_name": "ensembl_orthology",
            "adapter_scope": "human-mouse orthology lookup",
            "input_required": "human gene symbol or Ensembl gene ID",
            "current_status": "implemented_live_optional",
            "offline_fixture_available": "yes",
            "live_mode_available": "yes",
            "batch_mode_available": "no",
            "ci_enabled": "fixture_only",
            "privacy_risk": "low",
            "next_required_work": "MGI cross-check and ambiguity policy",
        },
        {
            "adapter_name": "live_ecd_validation",
            "adapter_scope": "ECD boundary, sequence extraction, and ECD identity comparison",
            "input_required": "UniProt accession plus orthology evidence",
            "current_status": "implemented_live_optional",
            "offline_fixture_available": "yes",
            "live_mode_available": "yes",
            "batch_mode_available": "no",
            "ci_enabled": "fixture_only",
            "privacy_risk": "low",
            "next_required_work": "batch mode with cassettes and conflict review",
        },
        {
            "adapter_name": "hpa",
            "adapter_scope": "normal-tissue RNA/protein evidence",
            "input_required": "gene symbol or Ensembl gene ID",
            "current_status": "implemented_fixture",
            "offline_fixture_available": "yes",
            "live_mode_available": "optional_not_production",
            "batch_mode_available": "no",
            "ci_enabled": "fixture_only",
            "privacy_risk": "medium",
            "next_required_work": "expanded HPA/GTEx normal-tissue adapter",
        },
        {
            "adapter_name": "gtex",
            "adapter_scope": "normal-tissue expression evidence",
            "input_required": "gene symbol or Ensembl gene ID",
            "current_status": "adapter_not_implemented",
            "offline_fixture_available": "no",
            "live_mode_available": "no",
            "batch_mode_available": "no",
            "ci_enabled": "no",
            "privacy_risk": "medium",
            "next_required_work": "implement GTEx adapter with missingness semantics",
        },
        {
            "adapter_name": "opentargets",
            "adapter_scope": "target, disease, tractability, drug and association evidence",
            "input_required": "gene symbol or Ensembl gene ID",
            "current_status": "adapter_not_implemented",
            "offline_fixture_available": "no",
            "live_mode_available": "no",
            "batch_mode_available": "no",
            "ci_enabled": "no",
            "privacy_risk": "medium",
            "next_required_work": "implement fixture-backed Open Targets adapter",
        },
        {
            "adapter_name": "chembl",
            "adapter_scope": "drug and biologic target evidence",
            "input_required": "target identifier",
            "current_status": "adapter_not_implemented",
            "offline_fixture_available": "no",
            "live_mode_available": "no",
            "batch_mode_available": "no",
            "ci_enabled": "no",
            "privacy_risk": "medium",
            "next_required_work": "implement fixture-backed ChEMBL adapter",
        },
        {
            "adapter_name": "clinicaltrials",
            "adapter_scope": "clinical and CAR/ADC evidence context",
            "input_required": "target symbol and disease context",
            "current_status": "planned",
            "offline_fixture_available": "no",
            "live_mode_available": "no",
            "batch_mode_available": "no",
            "ci_enabled": "no",
            "privacy_risk": "medium",
            "next_required_work": "define source and query strategy",
        },
        {
            "adapter_name": "local_tabular_evidence",
            "adapter_scope": "user-provided local evidence tables",
            "input_required": "local TSV or JSON evidence files",
            "current_status": "implemented_local_only",
            "offline_fixture_available": "not_applicable",
            "live_mode_available": "not_applicable",
            "batch_mode_available": "yes",
            "ci_enabled": "fixture_only",
            "privacy_risk": "medium",
            "next_required_work": "keep private source files gitignored",
        },
        {
            "adapter_name": "construct_planner",
            "adapter_scope": "ECD construct and stop-condition planning",
            "input_required": "screening table with ECD/topology fields",
            "current_status": "implemented_local_only",
            "offline_fixture_available": "yes",
            "live_mode_available": "not_applicable",
            "batch_mode_available": "yes",
            "ci_enabled": "yes",
            "privacy_risk": "low",
            "next_required_work": "add vector-orientation templates",
        },
        {
            "adapter_name": "screening_strategy",
            "adapter_scope": "antigen format strategy",
            "input_required": "antigen readiness table",
            "current_status": "implemented_local_only",
            "offline_fixture_available": "yes",
            "live_mode_available": "not_applicable",
            "batch_mode_available": "yes",
            "ci_enabled": "yes",
            "privacy_risk": "low",
            "next_required_work": "expand strategy templates",
        },
        {
            "adapter_name": "validation_ladder",
            "adapter_scope": "antibody validation planning",
            "input_required": "screening strategy plan",
            "current_status": "implemented_local_only",
            "offline_fixture_available": "yes",
            "live_mode_available": "not_applicable",
            "batch_mode_available": "yes",
            "ci_enabled": "yes",
            "privacy_risk": "low",
            "next_required_work": "connect to experimental tracking",
        },
    ]


def _status_from_hpa(row: Mapping[str, Any] | None) -> tuple[str, str]:
    if row is None:
        return "adapter_not_run", "adapter_not_run"
    evidence_status = str(row.get("evidence_status") or "").strip()
    risk = str(row.get("normal_tissue_risk") or "").strip()
    if evidence_status == "confirmed_fixture" or risk in {"low", "medium", "high"}:
        return "confirmed_fixture", "fixture_only"
    if evidence_status == "error":
        return "query_error", "query_error"
    if risk == "unknown" or evidence_status == "missing":
        return "source_record_missing", "source_record_missing"
    return "source_field_missing", "source_field_missing"


def _construct_status(row: Mapping[str, Any]) -> tuple[str, str]:
    gate = str(row.get("constructability_gate") or "").strip()
    ecd = str(row.get("ecd_region") or "").strip()
    if gate in {"pass", "partial"}:
        return "covered", "not_applicable_to_modality"
    if not _nonempty(ecd):
        return "missing", "insufficient_ecd_boundary"
    return "not_applicable", "not_applicable_to_modality"


def _live_ecd_status(records: list[Mapping[str, Any]]) -> tuple[str, str]:
    for record in records:
        if str(record.get("evidence_type")) in {"live_computed_ecd_identity", "live_human_ecd_boundary"}:
            status = str(record.get("evidence_status") or "")
            if status in {"confirmed_live", "confirmed_fixture", "inferred_live"}:
                return status, "fixture_only" if status == "confirmed_fixture" else "not_applicable_to_modality"
            if status == "error":
                return "query_error", "query_error"
    return "adapter_not_run", "adapter_not_run"


def _pick_primary_reason(reasons: list[str], modality: str) -> str:
    ordered = [
        "query_error",
        "source_record_missing",
        "insufficient_topology",
        "insufficient_ecd_boundary",
        "insufficient_orthology",
        "adapter_not_run",
        "id_mapping_missing",
        "adapter_not_implemented",
        "fixture_only",
        "coverage_pending",
        "not_applicable_to_modality",
    ]
    if modality in {"car_t", "adc", "bispecific"} and "source_record_missing" in reasons:
        return "source_record_missing"
    for reason in ordered:
        if reason in reasons:
            return reason
    return "unknown"


def _rescue_action(primary: str, id_row: Mapping[str, Any], modality: str) -> str:
    if primary == "id_mapping_missing":
        if not id_row.get("resolved_uniprot"):
            return "add_uniprot_accession"
        return "add_ensembl_gene_id"
    if primary in {"id_mapping_ambiguous", "conflicting_sources"}:
        return "manual_review_alias"
    if primary in {"source_record_missing", "source_field_missing"}:
        return "manual_review_normal_tissue" if modality in {"car_t", "adc", "bispecific"} else "run_hpa_adapter"
    if primary == "adapter_not_run":
        return "run_hpa_adapter"
    if primary == "adapter_not_implemented":
        return "run_opentargets_adapter"
    if primary == "insufficient_ecd_boundary":
        return "manual_review_topology"
    if primary == "insufficient_orthology":
        return "add_ensembl_gene_id"
    return "not_applicable_no_action"


def build_coverage_diagnostics(
    screening_rows: list[Mapping[str, Any]],
    *,
    evidence_records: list[Mapping[str, Any]] | None = None,
    normal_tissue_rows: list[Mapping[str, Any]] | None = None,
    alias_map: Mapping[str, Any] | None = None,
    uniprot_map: Mapping[str, Any] | None = None,
    ensembl_map: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    evidence_records = evidence_records or []
    id_rows = rescue_candidates(screening_rows, alias_map=alias_map, uniprot_map=uniprot_map, ensembl_map=ensembl_map)
    id_by_candidate = {row["candidate_id"]: row for row in id_rows}
    evidence_by_candidate = _by_candidate(evidence_records)
    hpa_by_key = _row_by_candidate_or_symbol(normal_tissue_rows or [])

    coverage_rows: list[dict[str, str]] = []
    for row in screening_rows:
        candidate_id = str(row.get("candidate_id") or "")
        gene_symbol = str(row.get("gene_symbol") or row.get("input_name") or "").upper()
        modality = str(row.get("modality") or "").lower()
        id_row = id_by_candidate.get(candidate_id, {})
        evidence_rows = list(evidence_by_candidate.get(candidate_id, []))
        hpa_row = hpa_by_key.get(candidate_id) or hpa_by_key.get(gene_symbol)

        mapping_status = str(id_row.get("mapping_status") or "not_checked")
        hgnc_status = mapping_status if mapping_status in {"resolved_exact", "resolved_alias", "ambiguous_alias", "conflict", "missing_identifier"} else "not_checked"
        uniprot = str(row.get("uniprot_accession") or row.get("human_uniprot_entry") or id_row.get("resolved_uniprot") or "")
        ensembl = str(row.get("ensembl_gene_id") or id_row.get("resolved_ensembl") or "")
        uniprot_status = "confirmed_local_xlsx" if uniprot else "id_mapping_missing"
        ensembl_status = "confirmed_local_xlsx" if ensembl else "id_mapping_missing"
        mouse_gate = str(row.get("mouse_model_transferability_gate") or "")
        mouse_status = "confirmed_local_xlsx" if mouse_gate in {"pass", "fail"} else "insufficient_orthology"
        hpa_status, hpa_reason = _status_from_hpa(hpa_row)
        construct_status, construct_reason = _construct_status(row)
        live_ecd_status, live_ecd_reason = _live_ecd_status(evidence_rows)
        drug_status = "local_context_available" if _nonempty(row.get("known_evidence")) and str(row.get("known_evidence")) != "0" else "adapter_not_implemented"

        reasons: list[str] = []
        if mapping_status == "missing_identifier":
            reasons.append("id_mapping_missing")
        elif mapping_status == "ambiguous_alias":
            reasons.append("id_mapping_ambiguous")
        elif mapping_status == "conflict":
            reasons.append("conflicting_sources")
        if not ensembl:
            reasons.append("id_mapping_missing" if not uniprot else "insufficient_orthology")
        if hpa_reason in MISSING_REASONS:
            reasons.append(hpa_reason)
        reasons.extend(["adapter_not_implemented", "adapter_not_implemented", "adapter_not_implemented"])
        if construct_reason != "not_applicable_to_modality":
            reasons.append(construct_reason)
        if mouse_status == "insufficient_orthology":
            reasons.append("insufficient_orthology")
        if live_ecd_reason == "adapter_not_run":
            reasons.append("adapter_not_run")
        if str(row.get("normal_tissue_risk") or "") == "unknown":
            reasons.append("source_record_missing")
        if mapping_status == "missing_identifier":
            primary = "id_mapping_missing"
        elif mapping_status == "ambiguous_alias":
            primary = "id_mapping_ambiguous"
        elif mapping_status == "conflict":
            primary = "conflicting_sources"
        else:
            primary = _pick_primary_reason(reasons, modality)
        secondary = sorted(set(reason for reason in reasons if reason != primary and reason in MISSING_REASONS))
        confidence = "medium"
        if primary in {"id_mapping_ambiguous", "conflicting_sources", "query_error"}:
            confidence = "low"
        elif primary in {"source_record_missing", "adapter_not_run", "adapter_not_implemented", "fixture_only"}:
            confidence = "medium"
        elif primary == "not_applicable_to_modality":
            confidence = "high"

        coverage_rows.append(
            {
                "candidate_id": candidate_id,
                "gene_symbol": gene_symbol,
                "species": str(row.get("species") or "human"),
                "input_identifier": str(row.get("input_name") or gene_symbol or uniprot or ensembl),
                "resolved_gene_symbol": str(id_row.get("resolved_symbol") or gene_symbol),
                "hgnc_status": hgnc_status,
                "uniprot_accession": uniprot,
                "uniprot_status": uniprot_status,
                "ensembl_gene_id": ensembl,
                "ensembl_status": ensembl_status,
                "mouse_ortholog_symbol": "",
                "mouse_ortholog_status": mouse_status,
                "hpa_status": hpa_status,
                "gtex_status": "adapter_not_implemented",
                "opentargets_status": "adapter_not_implemented",
                "chembl_status": "adapter_not_implemented",
                "clinicaltrials_status": "planned",
                "normal_tissue_status": hpa_status if hpa_status != "confirmed_fixture" else str(hpa_row.get("normal_tissue_risk") or "confirmed_fixture"),
                "drug_evidence_status": drug_status,
                "construct_status": construct_status,
                "live_ecd_status": live_ecd_status,
                "evidence_status_overall": "conflict" if primary == "conflicting_sources" else "missing",
                "missing_reason_primary": primary,
                "missing_reason_secondary": ";".join(secondary),
                "recommended_rescue_action": _rescue_action(primary, id_row, modality),
                "confidence": confidence,
                "notes": "coverage gap; follow-up required",
            }
        )

    matrix = adapter_readiness_matrix()
    summary = summarize_missingness(coverage_rows, matrix)
    return coverage_rows, id_rows, matrix, summary


def summarize_missingness(coverage_rows: list[Mapping[str, Any]], matrix: list[Mapping[str, Any]]) -> dict[str, Any]:
    primary = Counter(str(row.get("missing_reason_primary") or "unknown") for row in coverage_rows)
    overall = Counter(str(row.get("evidence_status_overall") or "unknown") for row in coverage_rows)
    hpa = Counter(str(row.get("hpa_status") or "unknown") for row in coverage_rows)
    adapter_status = Counter(str(row.get("current_status") or "unknown") for row in matrix)
    return {
        "status": "pass",
        "candidate_count": len(coverage_rows),
        "missing_reason_primary_counts": dict(sorted(primary.items())),
        "evidence_status_overall_counts": dict(sorted(overall.items())),
        "hpa_status_counts": dict(sorted(hpa.items())),
        "adapter_current_status_counts": dict(sorted(adapter_status.items())),
        "interpretation": "missing evidence is not negative evidence",
    }


def write_coverage_report(path: Path, summary: Mapping[str, Any]) -> None:
    lines = [
        "# Coverage Diagnostics Report",
        "",
        f"Status: {summary.get('status', 'unknown')}",
        f"Candidate count: {summary.get('candidate_count', 0)}",
        "",
        "## Primary Missing Reasons",
    ]
    for reason, count in dict(summary.get("missing_reason_primary_counts", {})).items():
        lines.append(f"- {reason}: {count}")
    lines.extend(
        [
            "",
            "## Adapter Readiness",
        ]
    )
    for status, count in dict(summary.get("adapter_current_status_counts", {})).items():
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Missing evidence is a coverage gap, not negative evidence. Missing normal-tissue evidence is not low risk, and missing drug evidence is not no druggability.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_coverage_diagnostics(
    *,
    screening_table: Path,
    outdir: Path,
    evidence_records_path: Path | None = None,
    normal_tissue_risk_path: Path | None = None,
    alias_map: Mapping[str, Any] | None = None,
    uniprot_map: Mapping[str, Any] | None = None,
    ensembl_map: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    screening_rows = read_tsv(screening_table)
    evidence_records = read_jsonl(evidence_records_path)
    normal_tissue_rows = read_tsv(normal_tissue_risk_path) if normal_tissue_risk_path and normal_tissue_risk_path.exists() else []
    coverage_rows, id_rows, matrix, summary = build_coverage_diagnostics(
        screening_rows,
        evidence_records=evidence_records,
        normal_tissue_rows=normal_tissue_rows,
        alias_map=alias_map,
        uniprot_map=uniprot_map,
        ensembl_map=ensembl_map,
    )
    outdir.mkdir(parents=True, exist_ok=True)
    coverage_path = outdir / "coverage_diagnostics.tsv"
    id_path = outdir / "id_mapping_rescue.tsv"
    matrix_path = outdir / "adapter_readiness_matrix.tsv"
    summary_path = outdir / "missingness_reason_summary.json"
    report_path = outdir / "coverage_report.md"
    write_tsv(coverage_path, coverage_rows, COVERAGE_DIAGNOSTICS_COLUMNS)
    write_tsv(id_path, id_rows, ID_MAPPING_RESCUE_COLUMNS)
    write_tsv(matrix_path, matrix, ADAPTER_READINESS_COLUMNS)
    summary = {
        **summary,
        "outputs": {
            "coverage_diagnostics": str(coverage_path),
            "id_mapping_rescue": str(id_path),
            "adapter_readiness_matrix": str(matrix_path),
            "missingness_reason_summary": str(summary_path),
            "coverage_report": str(report_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_coverage_report(report_path, summary)
    return summary
