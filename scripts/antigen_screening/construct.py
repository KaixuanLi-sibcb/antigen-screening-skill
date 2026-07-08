from __future__ import annotations

from .io import CONSTRUCT_COLUMNS


def construct_plan_for(row: dict[str, str]) -> dict[str, str]:
    base = {column: "" for column in CONSTRUCT_COLUMNS}
    base.update(
        {
            "gene_symbol": row.get("gene_symbol", ""),
            "modality": row.get("modality", ""),
            "accessibility_gate": row.get("accessibility_gate", ""),
            "constructability_gate": row.get("constructability_gate", ""),
            "ecd_region": row.get("ecd_region", ""),
            "ecd_length": row.get("ecd_length", ""),
            "construct_risks": row.get("risk_flags", ""),
            "evidence_state": row.get("ecd_evidence_state", ""),
        }
    )

    if row.get("accessibility_gate") == "fail" or "intracellular_or_nuclear" in row.get("risk_flags", ""):
        base.update(
            {
                "construct_recommendation": "no_construct",
                "construct_variant_1": "not_applicable",
                "construct_variant_2": "not_applicable",
                "include_signal_peptide": "no",
                "remove_tm": "not_applicable",
                "remove_cytoplasmic_tail": "not_applicable",
                "tag_strategy": "not_applicable",
                "display_strategy": "none",
                "expression_system": "not_applicable",
                "qc_plan": "confirm localization only if target is reconsidered",
                "stop_condition": "surface antigen accessibility failed",
            }
        )
        return base

    if "secreted_not_cell_surface" in row.get("risk_flags", ""):
        base.update(
            {
                "construct_recommendation": "soluble_protein_control_only",
                "construct_variant_1": "mature secreted protein with C-terminal His-Avi",
                "construct_variant_2": "commercial purified protein or expression-positive control",
                "include_signal_peptide": "use secretion leader in expression vector, exclude from mature antigen coordinates",
                "remove_tm": "not_applicable",
                "remove_cytoplasmic_tail": "not_applicable",
                "tag_strategy": "C-terminal His-Avi or Fc only for assay control",
                "display_strategy": "soluble control; not CAR surface target",
                "expression_system": "HEK293/Expi293 or source purified protein",
                "qc_plan": "SDS-PAGE, SEC, concentration, assay background check",
                "stop_condition": "not a cell-surface target for requested modality",
            }
        )
        return base

    construct_class = row.get("constructability_class", "")
    if row.get("constructability_gate") == "fail":
        base.update(
            {
                "construct_recommendation": "defer_construct",
                "construct_variant_1": "obtain topology and ECD boundary first",
                "construct_variant_2": "consider full-length cell display only after surface evidence",
                "include_signal_peptide": "unknown",
                "remove_tm": "unknown",
                "remove_cytoplasmic_tail": "unknown",
                "tag_strategy": "not_recommended",
                "display_strategy": "none",
                "expression_system": "not_applicable",
                "qc_plan": "topology validation required before construct work",
                "stop_condition": "constructability gate failed",
            }
        )
        return base

    if construct_class == "cell_display_or_loop_panel":
        base.update(
            {
                "construct_recommendation": "cell_display_fallback",
                "construct_variant_1": "full-length ORF cell-surface display",
                "construct_variant_2": "individual extracellular loop panel only as exploratory antigen",
                "include_signal_peptide": "native full-length context",
                "remove_tm": "no for cell display",
                "remove_cytoplasmic_tail": "no unless tag design requires truncation",
                "tag_strategy": "intracellular or minimally disruptive terminal tag",
                "display_strategy": "cell display",
                "expression_system": "mammalian cells",
                "qc_plan": "flow cytometry surface expression and ligand/antibody binding control",
                "stop_condition": "",
            }
        )
        return base

    if construct_class == "specialized_ecd_construct":
        length = int(row.get("ecd_length") or 0)
        if length and length < 150:
            recommendation = "short_ecd_multimer_or_fc"
            variant_2 = "ECD-AviTag/His for streptavidin multimerization"
            display = "Fc dimer or AviTag multimer"
        else:
            recommendation = "long_ecd_full_plus_domain_split"
            variant_2 = "domain-by-domain ECD fragment panel"
            display = "monomer first; optional Fc"
        base.update(
            {
                "construct_recommendation": recommendation,
                "construct_variant_1": "mature ECD with C-terminal His-Avi",
                "construct_variant_2": variant_2,
                "include_signal_peptide": "expression leader yes; mature ECD coordinates exclude cleaved signal peptide",
                "remove_tm": "yes",
                "remove_cytoplasmic_tail": "yes",
                "tag_strategy": "C-terminal His-Avi; optional Fc",
                "display_strategy": display,
                "expression_system": "HEK293/Expi293",
                "qc_plan": "plasmid sequence, SDS-PAGE reducing/non-reducing, SEC, binding QC if control exists",
                "stop_condition": "",
            }
        )
        return base

    base.update(
        {
            "construct_recommendation": "soluble_ecd_construct",
            "construct_variant_1": "mature ECD with C-terminal His-Avi",
            "construct_variant_2": "mature ECD-Fc if avidity or expression support is needed",
            "include_signal_peptide": "expression leader yes; mature ECD coordinates exclude cleaved signal peptide",
            "remove_tm": "yes",
            "remove_cytoplasmic_tail": "yes",
            "tag_strategy": "C-terminal His-Avi default; Fc optional",
            "display_strategy": "monomer first, Fc or Avi multimer second",
            "expression_system": "HEK293/Expi293",
            "qc_plan": "plasmid sequence, SDS-PAGE reducing/non-reducing, SEC, binding QC if control exists",
            "stop_condition": "",
        }
    )
    return base
