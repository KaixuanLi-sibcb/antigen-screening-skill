from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


RECORD_VERSION = "2.0"
ADAPTER_VERSION = "0.4.0"

EVIDENCE_STATUSES = {
    "confirmed_live",
    "confirmed_local_xlsx",
    "confirmed_fixture",
    "inferred_live",
    "inferred_local_xlsx",
    "missing",
    "not_applicable",
    "conflict",
    "error",
}

SOURCE_AUTHORITY_LEVELS = {
    "local_lab",
    "fixture",
    "curated_database",
    "public_database",
    "computed",
    "unknown",
}

CONFLICT_STATUSES = {
    "none",
    "value_conflict",
    "source_conflict",
    "version_conflict",
    "missing_conflict",
    "not_checked",
}


def _canonical_bytes(value: Any) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, Path):
        return value.read_bytes() if value.exists() else str(value).encode("utf-8")
    if isinstance(value, str):
        maybe_path = Path(value)
        if maybe_path.exists() and maybe_path.is_file():
            return maybe_path.read_bytes()
        return value.encode("utf-8")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")


def compute_raw_response_sha256(raw_response: Any) -> str:
    return hashlib.sha256(_canonical_bytes(raw_response)).hexdigest()


def normalize_evidence_status(status: str | None, source_kind: str = "fixture") -> str:
    raw = (status or "missing").strip().lower()
    aliases = {
        "confirmed": "confirmed_fixture" if source_kind == "fixture" else "confirmed_local_xlsx",
        "inferred": "inferred_local_xlsx" if source_kind == "local_xlsx" else "confirmed_fixture",
        "inferred_from_local_xlsx": "inferred_local_xlsx",
        "confirmed_local": "confirmed_local_xlsx",
        "fixture": "confirmed_fixture",
        "local_xlsx": "confirmed_local_xlsx",
    }
    normalized = aliases.get(raw, raw)
    return normalized if normalized in EVIDENCE_STATUSES else "error"


def make_evidence_record(
    *,
    candidate_id: str,
    gene_symbol: str,
    species: str = "",
    uniprot_accession: str = "",
    ensembl_gene_id: str = "",
    evidence_type: str,
    evidence_value: Any = "",
    normalized_value: Any = "",
    evidence_status: str,
    source_name: str,
    source_authority_level: str = "unknown",
    source_url: str = "",
    source_version: str = "",
    retrieved_at: str = "",
    query: Any = "",
    adapter_name: str = "antigen_screening",
    adapter_version: str = ADAPTER_VERSION,
    raw_response: Any = None,
    raw_response_sha256: str = "",
    confidence: str = "medium",
    conflict_status: str = "none",
    failure_mode: str = "",
    license_note: str = "",
) -> dict[str, str]:
    status = normalize_evidence_status(evidence_status)
    authority = source_authority_level if source_authority_level in SOURCE_AUTHORITY_LEVELS else "unknown"
    conflict = conflict_status if conflict_status in CONFLICT_STATUSES else "not_checked"
    value = "" if evidence_value is None else str(evidence_value)
    normalized = value if normalized_value in {None, ""} else str(normalized_value)
    if status == "missing":
        value = ""
        normalized = ""
        if not failure_mode:
            failure_mode = "evidence_missing"
        if confidence == "medium":
            confidence = "none"
    if status == "not_applicable" and not failure_mode:
        failure_mode = "not_applicable"
    if status == "conflict" and conflict in {"none", "not_checked"}:
        conflict = "value_conflict"
    raw_hash = raw_response_sha256 or (compute_raw_response_sha256(raw_response) if raw_response is not None else "")
    if not isinstance(query, str):
        query = json.dumps(query, ensure_ascii=False, sort_keys=True, default=str)
    return {
        "record_version": RECORD_VERSION,
        "candidate_id": candidate_id,
        "gene_symbol": gene_symbol,
        "species": species,
        "uniprot_accession": uniprot_accession,
        "ensembl_gene_id": ensembl_gene_id,
        "evidence_type": evidence_type,
        "evidence_value": value,
        "normalized_value": normalized,
        "evidence_status": status,
        "source_name": source_name,
        "source_authority_level": authority,
        "source_url": source_url,
        "source_version": source_version,
        "retrieved_at": retrieved_at,
        "query": query,
        "adapter_name": adapter_name,
        "adapter_version": adapter_version,
        "raw_response_sha256": raw_hash,
        "confidence": confidence,
        "conflict_status": conflict,
        "failure_mode": failure_mode,
        "license_note": license_note,
    }


def missing_evidence_record(
    *,
    candidate_id: str,
    gene_symbol: str,
    species: str = "",
    uniprot_accession: str = "",
    ensembl_gene_id: str = "",
    evidence_type: str,
    query: Any = "",
    source_name: str = "missing",
    failure_mode: str = "evidence_missing",
) -> dict[str, str]:
    return make_evidence_record(
        candidate_id=candidate_id,
        gene_symbol=gene_symbol,
        species=species,
        uniprot_accession=uniprot_accession,
        ensembl_gene_id=ensembl_gene_id,
        evidence_type=evidence_type,
        evidence_status="missing",
        source_name=source_name,
        source_authority_level="unknown",
        query=query,
        confidence="none",
        failure_mode=failure_mode,
        conflict_status="none",
    )


def fixture_evidence_record(
    *,
    candidate_id: str,
    gene_symbol: str,
    species: str = "human",
    uniprot_accession: str = "",
    evidence_type: str,
    evidence_value: Any = "",
    normalized_value: Any = "",
    fixture_source: str = "",
    query: Any = "",
    confidence: str = "medium",
) -> dict[str, str]:
    if evidence_value in {None, ""}:
        return missing_evidence_record(
            candidate_id=candidate_id,
            gene_symbol=gene_symbol,
            species=species,
            uniprot_accession=uniprot_accession,
            evidence_type=evidence_type,
            query=query,
            source_name="fixture_uniprot_like_json",
        )
    raw = {"fixture_source": fixture_source, "candidate_id": candidate_id, "evidence_type": evidence_type, "value": evidence_value}
    return make_evidence_record(
        candidate_id=candidate_id,
        gene_symbol=gene_symbol,
        species=species,
        uniprot_accession=uniprot_accession,
        evidence_type=evidence_type,
        evidence_value=evidence_value,
        normalized_value=normalized_value,
        evidence_status="confirmed_fixture",
        source_name="fixture_uniprot_like_json",
        source_authority_level="fixture",
        source_version="fixture_v1",
        query=query,
        raw_response=raw,
        confidence=confidence,
        license_note="Local fixture for offline smoke testing; not live database evidence.",
    )


def local_xlsx_evidence_record(
    *,
    candidate_id: str,
    gene_symbol: str,
    species: str = "human",
    uniprot_accession: str = "",
    evidence_type: str,
    evidence_value: Any = "",
    normalized_value: Any = "",
    evidence_status: str = "confirmed_local_xlsx",
    source_name: str = "local_tabular_evidence",
    source_version: str = "",
    query: Any = "",
    raw_payload: Any = None,
    confidence: str = "medium",
    failure_mode: str = "",
) -> dict[str, str]:
    status = normalize_evidence_status(evidence_status, source_kind="local_xlsx")
    if evidence_value in {None, ""} or status == "missing":
        return missing_evidence_record(
            candidate_id=candidate_id,
            gene_symbol=gene_symbol,
            species=species,
            uniprot_accession=uniprot_accession,
            evidence_type=evidence_type,
            query=query,
            source_name=source_name,
            failure_mode=failure_mode or "local_xlsx_value_missing",
        )
    return make_evidence_record(
        candidate_id=candidate_id,
        gene_symbol=gene_symbol,
        species=species,
        uniprot_accession=uniprot_accession,
        evidence_type=evidence_type,
        evidence_value=evidence_value,
        normalized_value=normalized_value,
        evidence_status=status,
        source_name=source_name,
        source_authority_level="local_lab",
        source_version=source_version,
        query=query,
        raw_response=raw_payload,
        confidence=confidence,
        failure_mode=failure_mode,
        license_note="Local user-provided evidence; private source files are excluded from Git.",
    )
