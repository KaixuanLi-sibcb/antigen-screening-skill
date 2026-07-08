from __future__ import annotations

from typing import Any


def evaluate_mouse_transferability(record: dict[str, Any] | None, threshold: float, requested: bool = False) -> dict[str, str]:
    if not requested:
        return {
            "mouse_model_transferability_gate": "not_applicable",
            "human_mouse_ecd_identity": "",
            "ecd_identity_threshold": f"{threshold:.2f}",
            "orthology_evidence_state": "not_applicable",
            "orthology_flags": "",
        }
    if not record:
        return {
            "mouse_model_transferability_gate": "uncertain",
            "human_mouse_ecd_identity": "",
            "ecd_identity_threshold": f"{threshold:.2f}",
            "orthology_evidence_state": "missing",
            "orthology_flags": "orthology_missing",
        }
    orthology = record.get("orthology") or {}
    value = orthology.get("human_mouse_ecd_identity")
    if value in ("", None):
        return {
            "mouse_model_transferability_gate": "uncertain",
            "human_mouse_ecd_identity": "",
            "ecd_identity_threshold": f"{threshold:.2f}",
            "orthology_evidence_state": "missing",
            "orthology_flags": "ecd_identity_missing",
        }
    identity = float(value)
    if identity > 1:
        identity = identity / 100.0
    gate = "pass" if identity >= threshold else "fail"
    return {
        "mouse_model_transferability_gate": gate,
        "human_mouse_ecd_identity": f"{identity:.3f}",
        "ecd_identity_threshold": f"{threshold:.2f}",
        "orthology_evidence_state": str(orthology.get("evidence_state") or "inferred"),
        "orthology_flags": "" if gate == "pass" else "mouse_ecd_identity_below_threshold",
    }
