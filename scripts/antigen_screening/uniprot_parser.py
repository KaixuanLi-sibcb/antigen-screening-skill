from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FEATURE_TYPE_MAP = {
    "signal peptide": "signal_peptide",
    "transmembrane": "transmembrane",
    "topological domain": "topological_domain",
    "chain": "chain",
    "domain": "domain",
    "glycosylation": "glycosylation",
    "disulfide bond": "disulfide_bond",
    "lipidation": "lipidation",
}


def _value(obj: Any) -> Any:
    if isinstance(obj, dict):
        if "value" in obj:
            return obj["value"]
        if "position" in obj:
            return obj["position"]
    return obj


def _int_or_none(obj: Any) -> int | None:
    value = _value(obj)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def feature_bounds(feature: dict[str, Any]) -> tuple[int | None, int | None]:
    location = feature.get("location") or {}
    start = location.get("start")
    end = location.get("end")
    return _int_or_none(start), _int_or_none(end)


def feature_type(feature_type_raw: str) -> str:
    return FEATURE_TYPE_MAP.get(feature_type_raw.strip().lower(), feature_type_raw.strip().lower().replace(" ", "_"))


def gene_symbol(raw: dict[str, Any]) -> str:
    if raw.get("gene_symbol"):
        return str(raw["gene_symbol"]).upper()
    for gene in raw.get("genes") or []:
        name = gene.get("geneName") or {}
        if name.get("value"):
            return str(name["value"]).upper()
    return ""


def protein_name(raw: dict[str, Any]) -> str:
    if raw.get("protein_name"):
        return str(raw["protein_name"])
    desc = raw.get("proteinDescription") or {}
    rec = desc.get("recommendedName") or {}
    full = rec.get("fullName") or {}
    return str(full.get("value") or raw.get("uniProtkbId") or "")


def accession(raw: dict[str, Any]) -> str:
    return str(raw.get("primaryAccession") or raw.get("accession") or "")


def sequence_length(raw: dict[str, Any]) -> int:
    seq = raw.get("sequence") or {}
    if isinstance(seq, dict):
        if seq.get("length"):
            return int(seq["length"])
        if seq.get("value"):
            return len(str(seq["value"]))
    if raw.get("sequence_length"):
        return int(raw["sequence_length"])
    return 0


def subcellular_locations(raw: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for item in raw.get("subcellular_location") or []:
        values.append(str(item))
    for comment in raw.get("comments") or []:
        if str(comment.get("commentType", "")).upper() != "SUBCELLULAR LOCATION":
            continue
        for loc in comment.get("subcellularLocations") or []:
            value = ((loc.get("location") or {}).get("value") or "").strip()
            if value:
                values.append(value)
    return sorted(set(values))


def normalize_uniprot_record(raw: dict[str, Any], source_path: str = "") -> dict[str, Any]:
    features = []
    for feature in raw.get("features") or []:
        start, end = feature_bounds(feature)
        features.append(
            {
                "type": feature_type(str(feature.get("type") or "")),
                "raw_type": str(feature.get("type") or ""),
                "start": start,
                "end": end,
                "description": str(feature.get("description") or ""),
                "evidence_state": str(feature.get("evidence_state") or raw.get("feature_evidence_state") or "confirmed"),
            }
        )
    return {
        "accession": accession(raw),
        "gene_symbol": gene_symbol(raw),
        "protein_name": protein_name(raw),
        "species": str(((raw.get("organism") or {}).get("scientificName") or raw.get("species") or "")).lower(),
        "sequence_length": sequence_length(raw),
        "features": features,
        "subcellular_locations": subcellular_locations(raw),
        "normal_tissue_risk": raw.get("normal_tissue_risk") or {"class": "unknown", "evidence_state": "missing", "notes": ""},
        "known_evidence": str(raw.get("known_evidence") or ""),
        "orthology": raw.get("orthology") or {},
        "isoform_ambiguity": bool(raw.get("isoform_ambiguity") or False),
        "source_path": source_path,
    }


def load_uniprot_json(path: Path) -> dict[str, Any]:
    return normalize_uniprot_record(json.loads(path.read_text(encoding="utf-8")), str(path))


def features_by_type(record: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [f for f in record.get("features", []) if f.get("type") == kind]


def fixture_index(fixtures_dir: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in sorted(fixtures_dir.glob("uniprot_*_*.json")):
        record = load_uniprot_json(path)
        if record["gene_symbol"]:
            index[record["gene_symbol"].upper()] = record
        if record["accession"]:
            index[record["accession"].upper()] = record
    return index
