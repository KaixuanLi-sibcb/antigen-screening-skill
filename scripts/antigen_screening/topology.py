from __future__ import annotations

from typing import Any

from .uniprot_parser import features_by_type


INTRACELLULAR_TERMS = ("nucleus", "nuclear", "cytoplasm", "cytosol", "mitochondr", "chromosome")


def _has_location(record: dict[str, Any], *terms: str) -> bool:
    text = " ".join(record.get("subcellular_locations") or []).lower()
    return any(term in text for term in terms)


def _extracellular_topological_domains(record: dict[str, Any]) -> list[dict[str, Any]]:
    domains = []
    for feature in features_by_type(record, "topological_domain"):
        desc = str(feature.get("description") or "").lower()
        if "extracellular" in desc or "lumenal" in desc or "luminal" in desc:
            domains.append(feature)
    return domains


def classify_accessibility(record: dict[str, Any] | None) -> dict[str, str]:
    if not record:
        return {
            "antigen_accessibility": "unknown",
            "accessibility_gate": "uncertain",
            "accessibility_evidence_state": "missing",
            "topology_evidence": "no local or live protein record",
            "topology_flags": "uniprot_record_missing",
        }

    tm = features_by_type(record, "transmembrane")
    signal = features_by_type(record, "signal_peptide")
    gpi = [f for f in record.get("features", []) if "gpi" in str(f.get("description", "")).lower()]
    extracellular_domains = _extracellular_topological_domains(record)
    locations = " ".join(record.get("subcellular_locations") or []).lower()

    if gpi:
        return {
            "antigen_accessibility": "gpi_anchored",
            "accessibility_gate": "pass",
            "accessibility_evidence_state": "confirmed",
            "topology_evidence": "GPI anchor feature",
            "topology_flags": "",
        }

    if len(tm) > 1:
        evidence_state = "confirmed" if "membrane" in locations or extracellular_domains else "inferred"
        return {
            "antigen_accessibility": "surface_multi_pass",
            "accessibility_gate": "pass",
            "accessibility_evidence_state": evidence_state,
            "topology_evidence": f"{len(tm)} transmembrane features",
            "topology_flags": "multi_pass",
        }

    if len(tm) == 1:
        if extracellular_domains:
            return {
                "antigen_accessibility": "surface_single_pass",
                "accessibility_gate": "pass",
                "accessibility_evidence_state": "confirmed",
                "topology_evidence": "single transmembrane feature plus extracellular topological domain",
                "topology_flags": "",
            }
        state = "inferred" if signal else "missing"
        gate = "pass" if signal else "uncertain"
        return {
            "antigen_accessibility": "surface_single_pass" if signal else "unknown_membrane_topology",
            "accessibility_gate": gate,
            "accessibility_evidence_state": state,
            "topology_evidence": "single transmembrane feature with inferred extracellular side" if signal else "single transmembrane feature without ECD topology",
            "topology_flags": "topology_inferred" if signal else "topology_missing",
        }

    if _has_location(record, "secreted"):
        return {
            "antigen_accessibility": "secreted",
            "accessibility_gate": "pass",
            "accessibility_evidence_state": "confirmed",
            "topology_evidence": "subcellular location: secreted",
            "topology_flags": "secreted_only",
        }

    if _has_location(record, "extracellular matrix", "extracellular space"):
        return {
            "antigen_accessibility": "extracellular_matrix",
            "accessibility_gate": "pass",
            "accessibility_evidence_state": "confirmed",
            "topology_evidence": "subcellular location: extracellular compartment",
            "topology_flags": "extracellular_not_cell_surface",
        }

    if signal:
        return {
            "antigen_accessibility": "secreted_or_lumenal_inferred",
            "accessibility_gate": "uncertain",
            "accessibility_evidence_state": "inferred",
            "topology_evidence": "signal peptide without TM or confirmed secreted location",
            "topology_flags": "topology_inferred",
        }

    if any(term in locations for term in INTRACELLULAR_TERMS):
        return {
            "antigen_accessibility": "intracellular_or_nuclear",
            "accessibility_gate": "fail",
            "accessibility_evidence_state": "confirmed",
            "topology_evidence": f"subcellular location: {', '.join(record.get('subcellular_locations') or [])}",
            "topology_flags": "intracellular_or_nuclear",
        }

    return {
        "antigen_accessibility": "unknown",
        "accessibility_gate": "uncertain",
        "accessibility_evidence_state": "missing",
        "topology_evidence": "no signal peptide, transmembrane, extracellular, or intracellular localization evidence parsed",
        "topology_flags": "topology_missing",
    }
