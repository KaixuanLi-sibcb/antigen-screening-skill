from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ID_MAPPING_RESCUE_COLUMNS = [
    "candidate_id",
    "input_symbol",
    "input_uniprot",
    "input_ensembl",
    "resolved_symbol",
    "resolved_uniprot",
    "resolved_ensembl",
    "mapping_method",
    "mapping_status",
    "alias_candidates",
    "ambiguous_candidates",
    "conflict_status",
    "recommended_action",
]

MAPPING_STATUSES = {
    "resolved_exact",
    "resolved_alias",
    "resolved_uniprot",
    "resolved_ensembl",
    "ambiguous_alias",
    "conflict",
    "missing_identifier",
    "not_checked",
    "error",
}


def normalize_symbol(value: str | None) -> str:
    return (value or "").strip().upper()


def _first_nonempty(row: Mapping[str, Any], names: list[str]) -> str:
    for name in names:
        value = str(row.get(name, "") or "").strip()
        if value:
            return value
    return ""


def _canonical_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [normalize_symbol(value)] if value.strip() else []
    if isinstance(value, Mapping):
        symbol = value.get("gene_symbol") or value.get("symbol") or value.get("resolved_symbol")
        return [normalize_symbol(str(symbol))] if symbol else []
    out: list[str] = []
    try:
        iterator = iter(value)
    except TypeError:
        return []
    for item in iterator:
        if isinstance(item, Mapping):
            symbol = item.get("gene_symbol") or item.get("symbol") or item.get("resolved_symbol")
            if symbol:
                out.append(normalize_symbol(str(symbol)))
        elif item:
            out.append(normalize_symbol(str(item)))
    return sorted(set(x for x in out if x))


def _metadata(value: Any) -> dict[str, str]:
    if isinstance(value, Mapping):
        return {
            "symbol": normalize_symbol(str(value.get("gene_symbol") or value.get("symbol") or value.get("resolved_symbol") or "")),
            "uniprot": str(value.get("uniprot_accession") or value.get("uniprot") or "").strip(),
            "ensembl": str(value.get("ensembl_gene_id") or value.get("ensembl") or "").strip(),
        }
    return {"symbol": "", "uniprot": "", "ensembl": ""}


def _lookup(mapping: Mapping[str, Any], key: str) -> Any:
    if not key:
        return None
    return mapping.get(key) or mapping.get(key.upper()) or mapping.get(key.lower())


def rescue_identifier(
    row: Mapping[str, Any],
    *,
    alias_map: Mapping[str, Any] | None = None,
    uniprot_map: Mapping[str, Any] | None = None,
    ensembl_map: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    alias_map = alias_map or {}
    uniprot_map = uniprot_map or {}
    ensembl_map = ensembl_map or {}

    candidate_id = _first_nonempty(row, ["candidate_id", "id", "input_id"])
    input_symbol = normalize_symbol(_first_nonempty(row, ["gene_symbol", "input_name", "target", "input_symbol"]))
    input_uniprot = _first_nonempty(row, ["uniprot_accession", "human_uniprot_entry", "input_uniprot"])
    input_ensembl = _first_nonempty(row, ["ensembl_gene_id", "input_ensembl"])

    if not any([input_symbol, input_uniprot, input_ensembl]):
        return {
            "candidate_id": candidate_id,
            "input_symbol": "",
            "input_uniprot": "",
            "input_ensembl": "",
            "resolved_symbol": "",
            "resolved_uniprot": "",
            "resolved_ensembl": "",
            "mapping_method": "none",
            "mapping_status": "missing_identifier",
            "alias_candidates": "",
            "ambiguous_candidates": "",
            "conflict_status": "missing_identifier",
            "recommended_action": "add_hgnc_mapping",
        }

    candidates: dict[str, str] = {}
    alias_candidates: list[str] = []
    ambiguous_candidates: list[str] = []
    resolved_uniprot = input_uniprot
    resolved_ensembl = input_ensembl

    if input_symbol:
        alias_value = _lookup(alias_map, input_symbol)
        if alias_value is not None:
            alias_candidates = _canonical_list(alias_value)
            if len(alias_candidates) > 1:
                ambiguous_candidates = alias_candidates
            elif alias_candidates:
                candidates["alias"] = alias_candidates[0]
        else:
            candidates["symbol"] = input_symbol

    if input_uniprot:
        meta = _metadata(_lookup(uniprot_map, input_uniprot))
        if meta["symbol"]:
            candidates["uniprot"] = meta["symbol"]
        if meta["uniprot"]:
            resolved_uniprot = meta["uniprot"]
        if meta["ensembl"] and not resolved_ensembl:
            resolved_ensembl = meta["ensembl"]

    if input_ensembl:
        meta = _metadata(_lookup(ensembl_map, input_ensembl))
        if meta["symbol"]:
            candidates["ensembl"] = meta["symbol"]
        if meta["uniprot"] and not resolved_uniprot:
            resolved_uniprot = meta["uniprot"]
        if meta["ensembl"]:
            resolved_ensembl = meta["ensembl"]

    if ambiguous_candidates:
        return {
            "candidate_id": candidate_id,
            "input_symbol": input_symbol,
            "input_uniprot": input_uniprot,
            "input_ensembl": input_ensembl,
            "resolved_symbol": "",
            "resolved_uniprot": resolved_uniprot,
            "resolved_ensembl": resolved_ensembl,
            "mapping_method": "alias",
            "mapping_status": "ambiguous_alias",
            "alias_candidates": ";".join(alias_candidates),
            "ambiguous_candidates": ";".join(ambiguous_candidates),
            "conflict_status": "ambiguous_alias",
            "recommended_action": "manual_review_alias",
        }

    unique_symbols = sorted(set(symbol for symbol in candidates.values() if symbol))
    if len(unique_symbols) > 1:
        return {
            "candidate_id": candidate_id,
            "input_symbol": input_symbol,
            "input_uniprot": input_uniprot,
            "input_ensembl": input_ensembl,
            "resolved_symbol": "",
            "resolved_uniprot": resolved_uniprot,
            "resolved_ensembl": resolved_ensembl,
            "mapping_method": "+".join(sorted(candidates)),
            "mapping_status": "conflict",
            "alias_candidates": ";".join(alias_candidates),
            "ambiguous_candidates": ";".join(unique_symbols),
            "conflict_status": "source_conflict",
            "recommended_action": "manual_review_alias",
        }

    resolved_symbol = unique_symbols[0] if unique_symbols else input_symbol
    if "uniprot" in candidates and not input_symbol:
        status = "resolved_uniprot"
        method = "uniprot"
        action = "not_applicable_no_action"
    elif "ensembl" in candidates and not input_symbol:
        status = "resolved_ensembl"
        method = "ensembl"
        action = "not_applicable_no_action"
    elif "alias" in candidates and input_symbol != resolved_symbol:
        status = "resolved_alias"
        method = "alias"
        action = "not_applicable_no_action"
    elif "uniprot" in candidates:
        status = "resolved_uniprot"
        method = "uniprot"
        action = "not_applicable_no_action"
    elif "ensembl" in candidates:
        status = "resolved_ensembl"
        method = "ensembl"
        action = "not_applicable_no_action"
    else:
        status = "resolved_exact"
        method = "symbol"
        action = "add_uniprot_accession" if not resolved_uniprot else "not_applicable_no_action"

    return {
        "candidate_id": candidate_id,
        "input_symbol": input_symbol,
        "input_uniprot": input_uniprot,
        "input_ensembl": input_ensembl,
        "resolved_symbol": resolved_symbol,
        "resolved_uniprot": resolved_uniprot,
        "resolved_ensembl": resolved_ensembl,
        "mapping_method": method,
        "mapping_status": status,
        "alias_candidates": ";".join(alias_candidates),
        "ambiguous_candidates": "",
        "conflict_status": "none",
        "recommended_action": action,
    }


def rescue_candidates(
    rows: list[Mapping[str, Any]],
    *,
    alias_map: Mapping[str, Any] | None = None,
    uniprot_map: Mapping[str, Any] | None = None,
    ensembl_map: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    return [rescue_identifier(row, alias_map=alias_map, uniprot_map=uniprot_map, ensembl_map=ensembl_map) for row in rows]
