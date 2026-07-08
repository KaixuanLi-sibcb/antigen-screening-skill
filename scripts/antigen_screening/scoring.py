from __future__ import annotations

from typing import Any

from .ecd import extract_ecd
from .evidence import fixture_evidence_record, missing_evidence_record
from .orthology import evaluate_mouse_transferability
from .topology import classify_accessibility


MODALITIES = {"antibody", "car_t", "adc", "bispecific", "soluble_ecd_screen", "unknown"}


def disease_gate(row: dict[str, str]) -> tuple[str, str]:
    text = f"{row.get('disease_context', '')} {row.get('user_evidence', '')}".lower()
    if "negative control" in text or "negative for" in text:
        return "fail", "confirmed"
    if text.strip():
        return "pass", "confirmed" if "manual" in text or "positive" in text else "inferred"
    return "uncertain", "missing"


def normal_risk(record: dict[str, Any] | None) -> tuple[str, str, str]:
    if not record:
        return "unknown", "missing", "normal tissue evidence missing"
    risk = record.get("normal_tissue_risk") or {}
    return str(risk.get("class") or "unknown"), str(risk.get("evidence_state") or "missing"), str(risk.get("notes") or "")


def constructability_gate(topology: dict[str, str], ecd: dict[str, str]) -> tuple[str, str]:
    access_gate = topology["accessibility_gate"]
    access = topology["antigen_accessibility"]
    flags = set(filter(None, (ecd.get("ecd_flags", "") + ";" + topology.get("topology_flags", "")).split(";")))
    length_class = ecd.get("ecd_length_class", "unknown")

    if access_gate == "fail" or "intracellular_or_nuclear" in flags or "no_ecd" in flags:
        return "fail", "no_ecd_construct"
    if access_gate == "uncertain":
        return "fail", "topology_required_before_construct"
    if "discontinuous_ecd" in flags or access == "surface_multi_pass":
        return "partial", "cell_display_or_loop_panel"
    if access == "secreted":
        return "partial", "secreted_protein_or_control"
    if length_class == "constructible_range":
        return "pass", "soluble_ecd_construct"
    if length_class in {"short", "long"}:
        return "partial", "specialized_ecd_construct"
    return "fail", "ecd_boundary_missing"


def modality_fit(row: dict[str, str], topology: dict[str, str], ecd: dict[str, str], risk: str) -> tuple[str, str, str, str]:
    modality = (row.get("modality") or "unknown").lower()
    access = topology["antigen_accessibility"]
    access_gate = topology["accessibility_gate"]

    if modality not in MODALITIES:
        modality = "unknown"

    if access_gate == "fail":
        return "not_fit_intracellular", "fail", "confirmed", "intracellular_or_nuclear"

    if modality in {"car_t", "adc"}:
        if access == "secreted":
            return "not_cell_surface_for_requested_modality", "fail", "confirmed", "secreted_not_cell_surface"
        if access in {"surface_single_pass", "surface_multi_pass", "gpi_anchored"}:
            if risk == "high":
                return "surface_but_high_normal_tissue_risk", "fail", "inferred", "high_normal_tissue_risk"
            return "surface_modality_plausible", "pass", "confirmed", ""
        return "surface_evidence_uncertain", "uncertain", "missing", "surface_evidence_missing"

    if modality == "antibody":
        if access in {"surface_single_pass", "surface_multi_pass", "gpi_anchored", "secreted", "extracellular_matrix"}:
            return "antibody_antigen_plausible", "pass", topology["accessibility_evidence_state"], ""
        return "antibody_surface_fit_uncertain", "uncertain", "missing", "surface_evidence_missing"

    if modality == "bispecific":
        if access in {"surface_single_pass", "surface_multi_pass", "gpi_anchored"}:
            return "bispecific_surface_target_plausible", "pass", topology["accessibility_evidence_state"], ""
        if access == "secreted":
            return "secreted_bispecific_context_required", "uncertain", "inferred", "secreted_only"
        return "bispecific_surface_fit_uncertain", "uncertain", "missing", "surface_evidence_missing"

    if modality == "soluble_ecd_screen":
        if ecd["ecd_evidence_state"] in {"confirmed", "inferred"}:
            return "soluble_antigen_screen_plausible", "pass", ecd["ecd_evidence_state"], ""
        return "ecd_missing_for_soluble_screen", "fail", "missing", "ecd_missing"

    return "modality_not_specified", "uncertain", "missing", "modality_missing"


def tie_break_score(
    topology: dict[str, str],
    ecd: dict[str, str],
    disease: str,
    risk: str,
    orthology: dict[str, str],
    modality_gate: str,
) -> int:
    score = 0
    if topology["accessibility_gate"] == "pass":
        score += 25
    elif topology["accessibility_gate"] == "uncertain":
        score -= 5
    else:
        score -= 40

    if ecd["ecd_evidence_state"] == "confirmed":
        score += 20
    elif ecd["ecd_evidence_state"] == "inferred":
        score += 10
    elif ecd["ecd_evidence_state"] == "missing":
        score -= 10

    if disease == "pass":
        score += 15
    elif disease == "fail":
        score -= 5

    if risk == "low":
        score += 10
    elif risk == "medium":
        score -= 5
    elif risk == "high":
        score -= 20

    if orthology["mouse_model_transferability_gate"] == "pass":
        score += 5
    elif orthology["mouse_model_transferability_gate"] == "fail":
        score -= 5

    if modality_gate == "pass":
        score += 15
    elif modality_gate == "fail":
        score -= 20

    return score


def priority_call(
    row: dict[str, str],
    topology: dict[str, str],
    modality_gate: str,
    construct_gate: str,
    mouse_gate: str,
    score: int,
    risk_flags: list[str],
) -> tuple[str, str]:
    modality = row.get("modality", "")
    if "secreted_not_cell_surface" in risk_flags and modality in {"car_t", "adc"}:
        return "control_or_not_applicable", "secreted protein may be useful as antigen/control but is not a cell-surface target for requested modality"
    if topology["accessibility_gate"] == "fail":
        return "no_go", "surface-antigen accessibility gate failed"
    if modality_gate == "fail":
        return "no_go", "requested modality gate failed"
    if mouse_gate == "fail":
        return "no_go", "mouse-model ECD transferability gate failed"
    if mouse_gate == "uncertain":
        return "conditional", "mouse-model ECD transferability is uncertain"
    if construct_gate == "fail":
        return "conditional", "antigen may be relevant but constructability requires more evidence or alternate display"
    if score >= 55:
        return "go", "all primary gates are compatible in fixture evidence"
    return "conditional", "plausible but one or more evidence areas remain weak or missing"


def evaluate_candidate(
    row: dict[str, str],
    record: dict[str, Any] | None,
    threshold: float,
    mouse_model_requested: bool = False,
) -> tuple[dict[str, str], list[dict[str, str]], list[dict[str, str]]]:
    topology = classify_accessibility(record)
    ecd = extract_ecd(record, topology)
    disease, disease_state = disease_gate(row)
    risk, risk_state, risk_notes = normal_risk(record)
    orthology = evaluate_mouse_transferability(record, threshold, mouse_model_requested)
    construct_gate, construct_class = constructability_gate(topology, ecd)
    fit, modality_gate, modality_state, modality_flag = modality_fit(row, topology, ecd, risk)

    flags = []
    for source in (topology.get("topology_flags", ""), ecd.get("ecd_flags", ""), orthology.get("orthology_flags", ""), modality_flag):
        flags.extend([item for item in source.split(";") if item])
    if risk == "high":
        flags.append("high_normal_tissue_risk")
    if record and record.get("isoform_ambiguity"):
        flags.append("isoform_ambiguity")
    if disease == "fail":
        flags.append("disease_relevance_negative_or_control")
    flags = sorted(set(flags))

    score = tie_break_score(topology, ecd, disease, risk, orthology, modality_gate)
    priority, rationale = priority_call(
        row,
        topology,
        modality_gate,
        construct_gate,
        orthology["mouse_model_transferability_gate"],
        score,
        flags,
    )
    missing = []
    if topology["accessibility_evidence_state"] == "missing":
        missing.append("topology")
    if ecd["ecd_evidence_state"] == "missing":
        missing.append("ecd_boundary")
    if risk_state == "missing":
        missing.append("normal_tissue")
    if orthology["orthology_evidence_state"] == "missing":
        missing.append("human_mouse_ecd_identity")
    if modality_state == "missing":
        missing.append("modality_evidence")

    out = {
        **row,
        "uniprot_accession": record.get("accession", "") if record else "",
        "protein_name": record.get("protein_name", "") if record else "",
        **topology,
        "ecd_region": ecd["ecd_region"],
        "ecd_length": ecd["ecd_length"],
        "ecd_evidence_state": ecd["ecd_evidence_state"],
        "ecd_boundary_confidence": ecd["ecd_boundary_confidence"],
        "ecd_notes": ecd["ecd_notes"],
        "isoform_risk": "isoform_ambiguity" if record and record.get("isoform_ambiguity") else "none_detected",
        "disease_relevance_gate": disease,
        "disease_evidence_state": disease_state,
        "normal_tissue_risk": risk,
        "normal_tissue_risk_evidence_state": risk_state,
        **{k: v for k, v in orthology.items() if k != "orthology_flags"},
        "constructability_gate": construct_gate,
        "constructability_class": construct_class,
        "modality_fit": fit,
        "modality_gate": modality_gate,
        "modality_evidence_state": modality_state,
        "known_evidence": record.get("known_evidence", "") if record else "",
        "risk_flags": ";".join(flags),
        "tie_break_score": str(score),
        "priority_call": priority,
        "decision_rationale": rationale,
        "missing_evidence": ";".join(missing),
    }

    risk_rows = [
        {
            "gene_symbol": row["gene_symbol"],
            "flag_type": flag,
            "severity": severity_for_flag(flag),
            "evidence": evidence_for_flag(flag, topology, ecd, risk_notes),
            "action": action_for_flag(flag),
        }
        for flag in flags
    ]
    evidence_rows = evidence_records(row, record, out)
    return out, evidence_rows, risk_rows


def severity_for_flag(flag: str) -> str:
    if flag in {"intracellular_or_nuclear", "high_normal_tissue_risk", "secreted_not_cell_surface", "no_ecd"}:
        return "high"
    if flag in {"discontinuous_ecd", "ecd_missing", "topology_missing", "mouse_ecd_identity_below_threshold", "isoform_ambiguity"}:
        return "medium"
    return "low"


def evidence_for_flag(flag: str, topology: dict[str, str], ecd: dict[str, str], risk_notes: str) -> str:
    if "normal_tissue" in flag:
        return risk_notes
    if "ecd" in flag or "secreted" in flag:
        return ecd.get("ecd_notes", "")
    return topology.get("topology_evidence", "")


def action_for_flag(flag: str) -> str:
    actions = {
        "intracellular_or_nuclear": "Do not design surface ECD construct.",
        "secreted_not_cell_surface": "Use as soluble antigen/control only unless surface-tethered evidence exists.",
        "high_normal_tissue_risk": "Review normal tissue expression and modality safety before prioritization.",
        "mouse_ecd_identity_below_threshold": "Do not assume mouse cross-reactivity; test binding directly.",
        "ecd_missing": "Obtain protein topology or sequence feature evidence.",
        "discontinuous_ecd": "Use cell-display or loop-level strategy, not forced soluble ECD.",
        "isoform_ambiguity": "Resolve isoform-specific ECD/TM architecture.",
    }
    return actions.get(flag, "Review before prioritization.")


def evidence_records(row: dict[str, str], record: dict[str, Any] | None, out: dict[str, str]) -> list[dict[str, str]]:
    source = record.get("source_path", "fixture_missing") if record else "fixture_missing"
    common = {
        "candidate_id": row["candidate_id"],
        "gene_symbol": row["gene_symbol"],
        "species": row.get("species", ""),
        "uniprot_accession": out.get("uniprot_accession", ""),
    }
    records: list[dict[str, str]] = []

    if out["accessibility_evidence_state"] == "missing":
        records.append(
            missing_evidence_record(
                candidate_id=row["candidate_id"],
                gene_symbol=row["gene_symbol"],
                species=row.get("species", ""),
                uniprot_accession=out.get("uniprot_accession", ""),
                evidence_type="topology",
                query={"gene_symbol": row["gene_symbol"], "source": source},
                source_name="fixture_uniprot_like_json",
            )
        )
    else:
        records.append(
            fixture_evidence_record(
                **common,
                evidence_type="topology",
                evidence_value=out["antigen_accessibility"],
                normalized_value=out["accessibility_gate"],
                fixture_source=source,
                query={"gene_symbol": row["gene_symbol"], "source": source},
                confidence="high" if out["accessibility_evidence_state"] == "confirmed" else "medium",
            )
        )

    if out["ecd_evidence_state"] == "missing":
        records.append(
            missing_evidence_record(
                candidate_id=row["candidate_id"],
                gene_symbol=row["gene_symbol"],
                species=row.get("species", ""),
                uniprot_accession=out.get("uniprot_accession", ""),
                evidence_type="ecd_boundary",
                query={"gene_symbol": row["gene_symbol"], "source": source},
                source_name="fixture_uniprot_like_json",
            )
        )
    else:
        records.append(
            fixture_evidence_record(
                **common,
                evidence_type="ecd_boundary",
                evidence_value=out["ecd_region"],
                normalized_value=out["ecd_length"],
                fixture_source=source,
                query={"gene_symbol": row["gene_symbol"], "source": source},
                confidence=out.get("ecd_boundary_confidence", "medium"),
            )
        )

    if out["normal_tissue_risk_evidence_state"] == "missing":
        records.append(
            missing_evidence_record(
                candidate_id=row["candidate_id"],
                gene_symbol=row["gene_symbol"],
                species=row.get("species", ""),
                uniprot_accession=out.get("uniprot_accession", ""),
                evidence_type="normal_tissue_risk",
                query={"gene_symbol": row["gene_symbol"], "source": source},
                source_name="fixture_uniprot_like_json",
            )
        )
    else:
        records.append(
            fixture_evidence_record(
                **common,
                evidence_type="normal_tissue_risk",
                evidence_value=out["normal_tissue_risk"],
                normalized_value=out["normal_tissue_risk"],
                fixture_source=source,
                query={"gene_symbol": row["gene_symbol"], "source": source},
                confidence="medium",
            )
        )

    if out["modality_evidence_state"] == "missing":
        records.append(
            missing_evidence_record(
                candidate_id=row["candidate_id"],
                gene_symbol=row["gene_symbol"],
                species=row.get("species", ""),
                uniprot_accession=out.get("uniprot_accession", ""),
                evidence_type="modality",
                query={"gene_symbol": row["gene_symbol"], "modality": row.get("modality", "")},
                source_name="fixture_gate_logic",
            )
        )
    else:
        records.append(
            fixture_evidence_record(
                **common,
                evidence_type="modality",
                evidence_value=out["modality_fit"],
                normalized_value=out["modality_gate"],
                fixture_source=f"gate_logic:{source}",
                query={"gene_symbol": row["gene_symbol"], "modality": row.get("modality", "")},
                confidence="medium",
            )
        )
    return records
