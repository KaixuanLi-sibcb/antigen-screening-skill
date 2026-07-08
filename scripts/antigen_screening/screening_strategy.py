from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .io import read_tsv, write_tsv


SCREENING_STRATEGY_COLUMNS = [
    "candidate_id",
    "gene_symbol",
    "antigen_readiness",
    "primary_strategy",
    "secondary_strategy",
    "screening_antigen_format",
    "display_context",
    "required_qc",
    "strategy_rationale",
    "not_recommended_reason",
]


def _flags(row: dict[str, str]) -> set[str]:
    return {flag for field in ("readiness_flags", "risk_flags") for flag in str(row.get(field, "")).split(";") if flag}


def strategy_for_row(row: dict[str, str]) -> dict[str, str]:
    flags = _flags(row)
    readiness = row.get("antigen_readiness") or row.get("readiness_gate") or ""
    accessibility = row.get("antigen_accessibility", "")
    rationale: list[str] = []
    not_recommended = ""
    primary = "soluble_ecd"
    secondary = "avitag_biotin_multimer"
    antigen_format = "monomeric soluble ECD without signal peptide, TM, or cytoplasmic tail"
    display_context = "soluble"
    qc = "SEC;reducing/nonreducing SDS-PAGE;binding-positive control if available"

    if readiness == "not_ready" or "accessibility_fail" in flags:
        primary = "not_recommended"
        secondary = ""
        antigen_format = "none"
        display_context = "none"
        qc = "stop before screening material production"
        not_recommended = row.get("stop_condition") or "antigen readiness failed"
        rationale.append("target is not ready for antibody screening material")
    elif "multi_pass_discontinuous_ecd" in flags or "cell_display_fallback" in flags or "multi" in accessibility:
        primary = "full_length_cell_display"
        secondary = "vlp_nanodisc_membrane_display"
        antigen_format = "full-length protein in native membrane context"
        display_context = "cell_surface_or_membrane_particle"
        qc = "surface expression flow QC;tag accessibility;negative-cell control;membrane prep QC"
        rationale.append("multi-pass or discontinuous ECD is better screened in membrane context")
    elif "secreted_soluble_antigen" in flags or "secreted" in accessibility:
        primary = "soluble_ecd"
        secondary = "fc_dimer"
        antigen_format = "secreted mature protein or soluble antigen control"
        display_context = "soluble"
        qc = "SEC;endotoxin;purity;orthogonal capture assay"
        rationale.append("secreted antigen is compatible with soluble screening but may not model a cell-surface target")
    elif "gpi_anchor" in flags or "gpi" in accessibility:
        primary = "soluble_ecd"
        secondary = "full_length_cell_display"
        antigen_format = "anchor-removed ECD plus optional full-length cell display"
        display_context = "soluble_and_cell_surface"
        qc = "anchor-removal boundary check;surface-display confirmatory assay"
        rationale.append("GPI anchor can be removed for soluble ECD but cell display may preserve native context")
    elif "short_ecd" in flags:
        primary = "avitag_biotin_multimer"
        secondary = "peptide_domain_fragment"
        antigen_format = "biotinylated multimer or constrained domain/peptide"
        display_context = "multimer_or_fragment"
        qc = "biotinylation efficiency;multimer assembly;competition with cell binding"
        rationale.append("short ECD benefits from avidity or constrained fragment strategy")
    elif "very_long_ecd" in flags or "long_ecd" in flags:
        primary = "fc_dimer"
        secondary = "peptide_domain_fragment"
        antigen_format = "Fc-stabilized ECD or mapped extracellular domain fragment"
        display_context = "soluble_or_fragment"
        qc = "expression yield;SEC;domain integrity;glycoform review"
        rationale.append("long ECD may require stabilization or domain-level screening")
    elif "cysteine_disulfide_risk" in flags or "glycosylation_risk" in flags:
        primary = "fc_dimer"
        secondary = "full_length_cell_display"
        antigen_format = "mammalian-expressed ECD with folding/glycosylation QC"
        display_context = "soluble_with_cell_validation"
        qc = "nonreducing SDS-PAGE;LC-MS/glycoform review;cell-binding orthogonal validation"
        rationale.append("folding or glycosylation risk requires mammalian expression and orthogonal cell validation")

    return {
        "candidate_id": row.get("candidate_id", ""),
        "gene_symbol": row.get("gene_symbol", ""),
        "antigen_readiness": readiness,
        "primary_strategy": primary,
        "secondary_strategy": secondary,
        "screening_antigen_format": antigen_format,
        "display_context": display_context,
        "required_qc": qc,
        "strategy_rationale": "; ".join(rationale) if rationale else "clean continuous ECD is compatible with soluble ECD screening",
        "not_recommended_reason": not_recommended,
    }


def run_screening_strategy(input_path: Path, outdir: Path) -> dict[str, Any]:
    rows = read_tsv(input_path)
    strategy_rows = [strategy_for_row(row) for row in rows]
    outdir.mkdir(parents=True, exist_ok=True)
    write_tsv(outdir / "screening_strategy_plan.tsv", strategy_rows, SCREENING_STRATEGY_COLUMNS)
    summary = {
        "status": "pass",
        "input": str(input_path),
        "outdir": str(outdir),
        "candidate_count": len(strategy_rows),
        "strategy_counts": dict(Counter(row["primary_strategy"] for row in strategy_rows)),
        "outputs": {"screening_strategy_plan": str(outdir / "screening_strategy_plan.tsv")},
    }
    (outdir / "screening_strategy_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
