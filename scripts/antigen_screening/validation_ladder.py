from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .io import read_tsv, write_tsv


VALIDATION_LADDER_COLUMNS = [
    "candidate_id",
    "gene_symbol",
    "validation_stage",
    "validation_goal",
    "recommended_assay",
    "required_controls",
    "pass_criterion",
    "trigger_condition",
    "priority",
    "notes",
]


BASE_STEPS = [
    {
        "validation_stage": "orthogonal_validation",
        "validation_goal": "confirm binding with an assay format independent of the discovery screen",
        "recommended_assay": "cell binding plus recombinant antigen or orthogonal capture assay",
        "required_controls": "isotype/background control;negative antigen control;positive antigen control when available",
        "pass_criterion": "signal is reproducible in an orthogonal format and tracks antigen-positive material",
        "trigger_condition": "all antibody hit workflows",
        "priority": "required",
    },
    {
        "validation_stage": "genetic_validation",
        "validation_goal": "show target-dependent binding through perturbation",
        "recommended_assay": "knockout, knockdown, CRISPRi, or rescue model",
        "required_controls": "non-targeting guide/siRNA;parental cells;viability and expression QC",
        "pass_criterion": "binding decreases after target loss and is restored by rescue when feasible",
        "trigger_condition": "cell model available",
        "priority": "required",
    },
    {
        "validation_stage": "independent_reagent_validation",
        "validation_goal": "reduce clone-specific or reagent-specific artifacts",
        "recommended_assay": "compare independent antibody clones or binder formats",
        "required_controls": "same antigen-positive and antigen-negative panel",
        "pass_criterion": "independent reagents show concordant target-dependent binding pattern",
        "trigger_condition": "multiple reagents or clones available",
        "priority": "required",
    },
    {
        "validation_stage": "tagged_protein_validation",
        "validation_goal": "confirm binding to tagged target in controlled expression context",
        "recommended_assay": "tagged full-length or ECD overexpression with tag-normalized readout",
        "required_controls": "empty vector;tag-only;expression-level matched cells",
        "pass_criterion": "binding increases with target expression and is not tag-only binding",
        "trigger_condition": "overexpression or rescue construct available",
        "priority": "recommended",
    },
    {
        "validation_stage": "flow_cell_binding_validation",
        "validation_goal": "verify binding on intact cells with native or near-native antigen presentation",
        "recommended_assay": "flow cytometry or high-content cell binding assay",
        "required_controls": "target-positive cells;target-negative cells;viability dye;Fc block when relevant",
        "pass_criterion": "specific signal separates target-positive from target-negative cells",
        "trigger_condition": "surface antigen or cell-display strategy",
        "priority": "required",
    },
    {
        "validation_stage": "knockout_knockdown_loss_of_binding",
        "validation_goal": "measure loss of antibody binding after target depletion",
        "recommended_assay": "KO/KD loss-of-binding flow or imaging assay",
        "required_controls": "multiple guides or siRNAs;on-target expression assay",
        "pass_criterion": "binding loss tracks target depletion and not unrelated toxicity",
        "trigger_condition": "genetic perturbation feasible",
        "priority": "required",
    },
    {
        "validation_stage": "overexpression_gain_of_binding",
        "validation_goal": "measure gain of antibody binding after target expression",
        "recommended_assay": "gain-of-binding assay in antigen-low or antigen-negative cells",
        "required_controls": "empty vector;expression matched control;tag-only control",
        "pass_criterion": "binding gain tracks target expression",
        "trigger_condition": "overexpression feasible",
        "priority": "required",
    },
    {
        "validation_stage": "immunocapture_ms_optional",
        "validation_goal": "identify captured target or unexpected binding partner",
        "recommended_assay": "immunocapture-MS or affinity purification-MS",
        "required_controls": "isotype control;bead-only control;negative cells",
        "pass_criterion": "intended antigen is enriched above controls",
        "trigger_condition": "binder specificity is uncertain or antigen identity needs orthogonal proof",
        "priority": "optional",
    },
]


def _needs_cross_species(row: dict[str, str]) -> bool:
    text = " ".join(str(row.get(field, "") or "").lower() for field in row)
    return "mouse" in text or "cross_species" in text or "mouse_model" in text


def ladder_for_row(row: dict[str, str]) -> list[dict[str, str]]:
    candidate_id = row.get("candidate_id", "")
    gene_symbol = row.get("gene_symbol", "")
    primary_strategy = row.get("primary_strategy", "")
    rows = []
    for step in BASE_STEPS:
        notes = ""
        if primary_strategy == "not_recommended":
            notes = "antigen strategy is not recommended; perform only if stop condition is resolved"
        elif primary_strategy in {"full_length_cell_display", "vlp_nanodisc_membrane_display"} and step["validation_stage"] in {"flow_cell_binding_validation", "tagged_protein_validation"}:
            notes = "prioritize native presentation and surface-expression QC"
        rows.append({"candidate_id": candidate_id, "gene_symbol": gene_symbol, **step, "notes": notes})
    if _needs_cross_species(row):
        rows.append(
            {
                "candidate_id": candidate_id,
                "gene_symbol": gene_symbol,
                "validation_stage": "cross_species_binding",
                "validation_goal": "test whether antibody binding transfers to mouse ortholog or mouse model material",
                "recommended_assay": "human and mouse antigen/cell binding side-by-side",
                "required_controls": "human target-positive;mouse ortholog-positive;negative cells;species-matched controls",
                "pass_criterion": "binding to mouse ECD or mouse cells is demonstrated directly when mouse model is required",
                "trigger_condition": "mouse model or cross-species claim",
                "priority": "required_if_mouse_model",
                "notes": "use ECD identity evidence as triage only; direct binding is required",
            }
        )
    return rows


def run_validation_ladder(input_path: Path, outdir: Path) -> dict[str, Any]:
    rows = read_tsv(input_path)
    ladder_rows: list[dict[str, str]] = []
    for row in rows:
        ladder_rows.extend(ladder_for_row(row))
    outdir.mkdir(parents=True, exist_ok=True)
    write_tsv(outdir / "validation_ladder.tsv", ladder_rows, VALIDATION_LADDER_COLUMNS)
    summary = {
        "status": "pass",
        "input": str(input_path),
        "outdir": str(outdir),
        "candidate_count": len(rows),
        "ladder_row_count": len(ladder_rows),
        "stage_counts": dict(Counter(row["validation_stage"] for row in ladder_rows)),
        "outputs": {"validation_ladder": str(outdir / "validation_ladder.tsv")},
    }
    (outdir / "validation_ladder_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
