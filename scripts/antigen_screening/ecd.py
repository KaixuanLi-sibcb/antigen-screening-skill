from __future__ import annotations

from typing import Any

from .uniprot_parser import features_by_type


def _length(start: int | None, end: int | None) -> int | None:
    if start is None or end is None:
        return None
    return max(0, end - start + 1)


def _len_class(length: int | None) -> str:
    if length is None or length <= 0:
        return "unknown"
    if 150 <= length <= 500:
        return "constructible_range"
    if 50 <= length < 150:
        return "short"
    if 501 <= length <= 800:
        return "long"
    return "difficult"


def _extracellular_domains(record: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for feature in features_by_type(record, "topological_domain"):
        desc = str(feature.get("description") or "").lower()
        if "extracellular" in desc or "lumenal" in desc or "luminal" in desc:
            out.append(feature)
    return out


def extract_ecd(record: dict[str, Any] | None, topology: dict[str, str]) -> dict[str, str]:
    if not record:
        return {
            "ecd_region": "missing",
            "ecd_length": "",
            "ecd_evidence_state": "missing",
            "ecd_boundary_confidence": "none",
            "ecd_notes": "no protein record",
            "ecd_length_class": "unknown",
            "ecd_flags": "ecd_missing",
        }

    access = topology.get("antigen_accessibility", "")
    if access == "intracellular_or_nuclear":
        return {
            "ecd_region": "not_applicable",
            "ecd_length": "",
            "ecd_evidence_state": "not_applicable",
            "ecd_boundary_confidence": "none",
            "ecd_notes": "intracellular or nuclear protein; no ECD construct",
            "ecd_length_class": "unknown",
            "ecd_flags": "no_ecd;intracellular_or_nuclear",
        }

    extracellular = _extracellular_domains(record)
    if extracellular:
        if len(extracellular) == 1:
            region = extracellular[0]
            length = _length(region.get("start"), region.get("end"))
            return {
                "ecd_region": f"{region.get('start')}-{region.get('end')}",
                "ecd_length": str(length or ""),
                "ecd_evidence_state": "confirmed",
                "ecd_boundary_confidence": "high",
                "ecd_notes": f"explicit extracellular topological domain: {region.get('description')}",
                "ecd_length_class": _len_class(length),
                "ecd_flags": "",
            }
        total = sum(_length(item.get("start"), item.get("end")) or 0 for item in extracellular)
        return {
            "ecd_region": ";".join(f"{item.get('start')}-{item.get('end')}" for item in extracellular),
            "ecd_length": str(total),
            "ecd_evidence_state": "confirmed",
            "ecd_boundary_confidence": "medium",
            "ecd_notes": "multiple extracellular loops; discontinuous soluble ECD is not native",
            "ecd_length_class": "difficult",
            "ecd_flags": "discontinuous_ecd",
        }

    tm = features_by_type(record, "transmembrane")
    signal = features_by_type(record, "signal_peptide")
    seq_len = int(record.get("sequence_length") or 0)

    if access == "surface_multi_pass":
        return {
            "ecd_region": "missing_or_discontinuous",
            "ecd_length": "",
            "ecd_evidence_state": "missing",
            "ecd_boundary_confidence": "none",
            "ecd_notes": "multi-pass protein without explicit extracellular loop boundaries",
            "ecd_length_class": "difficult",
            "ecd_flags": "discontinuous_ecd;ecd_missing",
        }

    if access == "surface_single_pass" and len(tm) == 1:
        signal_end = int(signal[0]["end"]) if signal and signal[0].get("end") else 0
        tm_start = int(tm[0]["start"]) if tm[0].get("start") else 0
        if tm_start > signal_end + 1:
            start = signal_end + 1
            end = tm_start - 1
            length = _length(start, end)
            return {
                "ecd_region": f"{start}-{end}",
                "ecd_length": str(length or ""),
                "ecd_evidence_state": "inferred",
                "ecd_boundary_confidence": "medium",
                "ecd_notes": "inferred from signal peptide and single transmembrane feature",
                "ecd_length_class": _len_class(length),
                "ecd_flags": "ecd_inferred",
            }

    if access in {"secreted", "secreted_or_lumenal_inferred", "extracellular_matrix"}:
        chains = features_by_type(record, "chain")
        if chains:
            chain = chains[0]
            start, end = chain.get("start"), chain.get("end")
            length = _length(start, end)
            state = "confirmed"
            confidence = "medium"
            note = "mature secreted chain"
        else:
            signal_end = int(signal[0]["end"]) if signal and signal[0].get("end") else 0
            start, end = signal_end + 1, seq_len or None
            length = _length(start, end)
            state = "inferred"
            confidence = "low"
            note = "inferred secreted mature region from signal peptide"
        return {
            "ecd_region": f"{start}-{end}" if start and end else "missing",
            "ecd_length": str(length or ""),
            "ecd_evidence_state": state,
            "ecd_boundary_confidence": confidence,
            "ecd_notes": note,
            "ecd_length_class": _len_class(length),
            "ecd_flags": "secreted_only",
        }

    return {
        "ecd_region": "missing",
        "ecd_length": "",
        "ecd_evidence_state": "missing",
        "ecd_boundary_confidence": "none",
        "ecd_notes": "no ECD boundary could be extracted",
        "ecd_length_class": "unknown",
        "ecd_flags": "ecd_missing",
    }
