from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .io import read_tsv, write_tsv


READINESS_COLUMNS = [
    "candidate_id",
    "gene_symbol",
    "modality",
    "antigen_accessibility",
    "accessibility_gate",
    "ecd_region",
    "ecd_length",
    "constructability_gate",
    "antigen_readiness",
    "readiness_gate",
    "readiness_score",
    "readiness_flags",
    "primary_screening_material",
    "fallback_screening_material",
    "readiness_rationale",
    "stop_condition",
]


def _text(row: dict[str, str], *fields: str) -> str:
    return " ".join(str(row.get(field, "") or "") for field in fields).lower()


def _int_or_none(value: object) -> int | None:
    try:
        text = str(value or "").strip()
        if not text or text == "not_applicable":
            return None
        return int(float(text))
    except ValueError:
        return None


def _flag_from_text(row: dict[str, str], terms: tuple[str, ...]) -> bool:
    text = _text(row, "protein_name", "ecd_notes", "known_evidence", "risk_flags", "constructability_class", "topology_evidence")
    return any(term in text for term in terms)


def readiness_for_row(row: dict[str, str]) -> dict[str, str]:
    accessibility = row.get("antigen_accessibility", "")
    access_gate = row.get("accessibility_gate", "")
    construct_gate = row.get("constructability_gate", "")
    modality = (row.get("modality") or "").lower()
    ecd_region = row.get("ecd_region", "")
    ecd_state = row.get("ecd_evidence_state", "")
    ecd_length = _int_or_none(row.get("ecd_length"))
    flags: list[str] = []
    reasons: list[str] = []
    stop = ""
    primary = "not_recommended"
    fallback = ""
    readiness = "ready"
    gate = "pass"
    score = 60

    if access_gate == "fail" or "intracellular" in accessibility or "nuclear" in accessibility:
        flags.append("accessibility_fail")
        reasons.append("surface-accessible antigen evidence failed")
        readiness = "not_ready"
        gate = "fail"
        score = -50
        stop = "no extracellularly accessible antigen for screening"
    elif access_gate == "uncertain":
        flags.append("accessibility_uncertain")
        reasons.append("surface accessibility is uncertain")
        readiness = "missing_evidence"
        gate = "uncertain"
        score -= 30

    if not stop and (ecd_state == "missing" or ecd_region in {"", "missing", "not_applicable", "missing_or_discontinuous"}):
        flags.append("ecd_missing")
        reasons.append("ECD boundary is missing or unsuitable")
        if "multi" not in accessibility:
            readiness = "missing_evidence"
            gate = "uncertain"
            score -= 25

    if "multi" in accessibility or "discontinuous" in _text(row, "ecd_notes", "risk_flags", "constructability_class", "ecd_region"):
        flags.extend(["multi_pass_discontinuous_ecd", "cell_display_fallback"])
        reasons.append("multi-pass or discontinuous ECD requires native display fallback")
        primary = "full_length_cell_display"
        fallback = "vlp_nanodisc_membrane_display"
        if readiness == "ready":
            readiness = "conditional"
            gate = "conditional"
        score -= 20

    if "secreted" in accessibility:
        flags.append("secreted_soluble_antigen")
        reasons.append("secreted antigen can be screened as soluble protein but is not a clean surface CAR/ADC target")
        primary = "soluble_secreted_protein"
        if modality in {"car_t", "car", "adc"} and readiness == "ready":
            readiness = "conditional"
            gate = "conditional"
            score -= 15

    if "gpi" in accessibility:
        flags.append("gpi_anchor")
        reasons.append("GPI anchor should be removed for soluble ECD or preserved by cell-display fallback")
        primary = "soluble_ecd_anchor_removed"
        fallback = fallback or "full_length_cell_display"
        if readiness == "ready":
            readiness = "conditional"
            gate = "conditional"
            score -= 5

    if ecd_length is not None:
        if ecd_length < 150:
            flags.append("short_ecd")
            reasons.append("short ECD may need multimerization or peptide/domain screening")
            primary = primary if primary != "not_recommended" else "avitag_biotin_multimer"
            fallback = fallback or "peptide_domain_fragment"
            if readiness == "ready":
                readiness = "conditional"
                gate = "conditional"
            score -= 10
        elif ecd_length > 800:
            flags.append("very_long_ecd")
            reasons.append("very long ECD is difficult for expression and screening")
            primary = primary if primary != "not_recommended" else "domain_fragment_or_cell_display"
            fallback = fallback or "full_length_cell_display"
            if readiness == "ready":
                readiness = "conditional"
                gate = "conditional"
            score -= 20
        elif ecd_length > 500:
            flags.append("long_ecd")
            reasons.append("long ECD may need Fc fusion, truncation, or expression optimization")
            primary = primary if primary != "not_recommended" else "fc_dimer_or_soluble_ecd"
            fallback = fallback or "domain_fragment"
            if readiness == "ready":
                readiness = "conditional"
                gate = "conditional"
            score -= 8

    if _flag_from_text(row, ("cysteine", "cys", "disulfide", "disulphide")):
        flags.append("cysteine_disulfide_risk")
        reasons.append("cysteine-rich or disulfide-rich ECD may complicate expression/folding")
        if readiness == "ready":
            readiness = "conditional"
            gate = "conditional"
        score -= 8

    if _flag_from_text(row, ("glycosylation", "glyco", "n-linked", "o-linked")):
        flags.append("glycosylation_risk")
        reasons.append("glycosylation may affect expression, folding, and antibody epitope presentation")
        if readiness == "ready":
            readiness = "conditional"
            gate = "conditional"
        score -= 8

    isoform = (row.get("isoform_risk") or "").strip().lower()
    if isoform and isoform not in {"none", "none_detected", "not_detected", "missing"}:
        flags.append("isoform_ambiguity")
        reasons.append("isoform ambiguity may alter ECD or TM architecture")
        if readiness == "ready":
            readiness = "conditional"
            gate = "conditional"
        score -= 15

    if construct_gate == "fail" and not stop:
        flags.append("constructability_fail")
        reasons.append("constructability gate failed")
        readiness = "not_ready"
        gate = "fail"
        score -= 40
        stop = "constructability gate failed"
    elif construct_gate == "partial" and readiness == "ready":
        flags.append("constructability_partial")
        reasons.append("constructability is partial and requires fallback strategy")
        readiness = "conditional"
        gate = "conditional"
        score -= 12

    if primary == "not_recommended" and readiness in {"ready", "conditional"}:
        primary = "soluble_ecd" if construct_gate == "pass" else "full_length_cell_display" if "cell_display_fallback" in flags else "fc_dimer_or_soluble_ecd"
    if readiness == "not_ready":
        primary = "not_recommended"

    flags = sorted(set(flags))
    return {
        "candidate_id": row.get("candidate_id", ""),
        "gene_symbol": row.get("gene_symbol", ""),
        "modality": row.get("modality", ""),
        "antigen_accessibility": accessibility,
        "accessibility_gate": access_gate,
        "ecd_region": ecd_region,
        "ecd_length": row.get("ecd_length", ""),
        "constructability_gate": construct_gate,
        "antigen_readiness": readiness,
        "readiness_gate": gate,
        "readiness_score": str(score),
        "readiness_flags": ";".join(flags),
        "primary_screening_material": primary,
        "fallback_screening_material": fallback,
        "readiness_rationale": "; ".join(reasons) if reasons else "clean continuous ECD is compatible with first-pass screening material",
        "stop_condition": stop,
    }


def run_antigen_readiness(input_path: Path, outdir: Path) -> dict[str, Any]:
    rows = read_tsv(input_path)
    readiness_rows = [readiness_for_row(row) for row in rows]
    outdir.mkdir(parents=True, exist_ok=True)
    write_tsv(outdir / "antigen_readiness_table.tsv", readiness_rows, READINESS_COLUMNS)
    counts = Counter(row["antigen_readiness"] for row in readiness_rows)
    flag_counts: Counter[str] = Counter()
    for row in readiness_rows:
        for flag in row["readiness_flags"].split(";"):
            if flag:
                flag_counts[flag] += 1
    summary = {
        "status": "pass",
        "input": str(input_path),
        "outdir": str(outdir),
        "candidate_count": len(readiness_rows),
        "readiness_counts": dict(counts),
        "flag_counts": dict(flag_counts),
        "outputs": {
            "antigen_readiness_table": str(outdir / "antigen_readiness_table.tsv"),
            "antigen_readiness_summary": str(outdir / "antigen_readiness_summary.json"),
        },
    }
    (outdir / "antigen_readiness_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
