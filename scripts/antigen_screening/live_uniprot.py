from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .evidence import compute_raw_response_sha256, make_evidence_record, missing_evidence_record
from .uniprot_parser import normalize_uniprot_record


UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"
UNIPROT_ENTRY = "https://rest.uniprot.org/uniprotkb/{accession}.json"
ADAPTER_NAME = "uniprot_live_adapter"
ADAPTER_VERSION = "0.5.0"

SPECIES_TO_TAXON = {
    "human": 9606,
    "homo sapiens": 9606,
    "mouse": 10090,
    "mus musculus": 10090,
}


def http_json(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "antigen-screening/0.5"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def search_accession(gene_symbol: str, species: str, timeout: int) -> str:
    taxon_id = SPECIES_TO_TAXON.get(species.lower(), 9606)
    query = f"(gene_exact:{gene_symbol}) AND (organism_id:{taxon_id}) AND (reviewed:true)"
    url = UNIPROT_SEARCH + "?" + urllib.parse.urlencode({"query": query, "format": "json", "size": "1"})
    data = http_json(url, timeout)
    results = data.get("results") or []
    return str(results[0].get("primaryAccession") or "") if results else ""


def fetch_entry(accession: str, timeout: int) -> dict[str, Any]:
    return http_json(UNIPROT_ENTRY.format(accession=urllib.parse.quote(accession)), timeout)


def reviewed_status(raw: dict[str, Any]) -> str:
    entry_type = str(raw.get("entryType") or "").lower()
    return "reviewed" if "reviewed" in entry_type or raw.get("reviewed") is True else "unreviewed"


def sequence_value(raw: dict[str, Any]) -> str:
    sequence = raw.get("sequence") or {}
    if isinstance(sequence, dict):
        return str(sequence.get("value") or "")
    return str(raw.get("sequence") or "")


def has_isoform_ambiguity(raw: dict[str, Any]) -> bool:
    if raw.get("isoform_ambiguity"):
        return True
    for comment in raw.get("comments") or []:
        if str(comment.get("commentType", "")).upper() == "ALTERNATIVE PRODUCTS":
            isoforms = comment.get("isoforms") or []
            if len(isoforms) > 1:
                return True
    return False


def load_uniprot_source(
    *,
    accession: str = "",
    gene_symbol: str = "",
    species: str = "human",
    offline_fixture: Path | None = None,
    no_network: bool = False,
    timeout: int = 20,
) -> tuple[str, dict[str, Any] | None, dict[str, str]]:
    if offline_fixture:
        try:
            raw = json.loads(offline_fixture.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return "error", None, {"error": f"{type(exc).__name__}: {exc}", "source_name": "fixture_uniprot_like_json"}
        return "fixture", raw, {"source_path": str(offline_fixture), "source_name": "fixture_uniprot_like_json"}

    if no_network:
        return "missing", None, {"error": "network disabled and no offline fixture supplied", "source_name": "uniprot_live"}

    try:
        resolved = accession or search_accession(gene_symbol, species, timeout)
        if not resolved:
            return "missing", None, {"error": "no reviewed UniProt accession found", "source_name": "uniprot_live"}
        raw = fetch_entry(resolved, timeout)
    except Exception as exc:  # noqa: BLE001
        return "error", None, {"error": f"{type(exc).__name__}: {exc}", "source_name": "uniprot_live"}
    return "live", raw, {"source_url": UNIPROT_ENTRY.format(accession=resolved), "source_name": "uniprot_live", "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def normalize_live_uniprot(raw: dict[str, Any], source_path: str = "") -> dict[str, Any]:
    normalized = normalize_uniprot_record(raw, source_path)
    normalized["review_status"] = reviewed_status(raw)
    normalized["sequence"] = sequence_value(raw)
    normalized["isoform_ambiguity"] = bool(normalized.get("isoform_ambiguity") or has_isoform_ambiguity(raw))
    return normalized


def _source_fields(kind: str, metadata: dict[str, str], raw: dict[str, Any] | None) -> dict[str, str]:
    if kind == "live":
        return {
            "evidence_status": "confirmed_live",
            "source_name": metadata.get("source_name", "uniprot_live"),
            "source_authority_level": "public_database",
            "source_url": metadata.get("source_url", ""),
            "source_version": "UniProtKB REST current",
            "retrieved_at": metadata.get("retrieved_at", ""),
            "raw_response_sha256": compute_raw_response_sha256(raw),
            "license_note": "UniProt live REST response; check UniProt terms before redistribution.",
        }
    return {
        "evidence_status": "confirmed_fixture",
        "source_name": metadata.get("source_name", "fixture_uniprot_like_json"),
        "source_authority_level": "fixture",
        "source_url": "",
        "source_version": "fixture_v1",
        "retrieved_at": "",
        "raw_response_sha256": compute_raw_response_sha256(raw),
        "license_note": "Local UniProt-like fixture for offline validation.",
    }


def uniprot_evidence_records(
    *,
    normalized: dict[str, Any] | None,
    raw: dict[str, Any] | None,
    kind: str,
    metadata: dict[str, str],
    candidate_id: str = "",
    gene_symbol: str = "",
    species: str = "human",
    query: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    query = query or {}
    source_name = metadata.get("source_name", "uniprot_live")
    if kind in {"missing", "error"} or raw is None or normalized is None:
        status = "error" if kind == "error" else "missing"
        return [
            make_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                evidence_type="uniprot_live_fetch",
                evidence_status=status,
                source_name=source_name,
                source_authority_level="public_database" if source_name == "uniprot_live" else "fixture",
                query=query,
                adapter_name=ADAPTER_NAME,
                adapter_version=ADAPTER_VERSION,
                confidence="none",
                failure_mode=metadata.get("error", "uniprot_fetch_unavailable"),
                conflict_status="none",
            )
        ]

    source_fields = _source_fields(kind, metadata, raw)
    common = {
        "candidate_id": candidate_id or normalized.get("accession", ""),
        "gene_symbol": gene_symbol or normalized.get("gene_symbol", ""),
        "species": species,
        "uniprot_accession": normalized.get("accession", ""),
        "query": query,
        "adapter_name": ADAPTER_NAME,
        "adapter_version": ADAPTER_VERSION,
        **source_fields,
    }
    records = [
        make_evidence_record(
            **common,
            evidence_type="uniprot_accession",
            evidence_value=normalized.get("accession", ""),
            normalized_value=normalized.get("accession", ""),
            confidence="high",
        ),
        make_evidence_record(
            **common,
            evidence_type="uniprot_review_status",
            evidence_value=normalized.get("review_status", ""),
            normalized_value=normalized.get("review_status", ""),
            confidence="high",
        ),
        make_evidence_record(
            **common,
            evidence_type="uniprot_sequence",
            evidence_value=str(len(normalized.get("sequence", ""))),
            normalized_value=str(len(normalized.get("sequence", ""))),
            confidence="high" if normalized.get("sequence") else "none",
        ),
    ]
    feature_types = {feature.get("type") for feature in normalized.get("features", [])}
    if feature_types & {"topological_domain", "transmembrane", "signal_peptide", "chain"}:
        records.append(
            make_evidence_record(
                **common,
                evidence_type="uniprot_topology_features",
                evidence_value=";".join(sorted(str(x) for x in feature_types if x)),
                normalized_value="topology_features_present",
                confidence="medium",
            )
        )
    else:
        records.append(
            missing_evidence_record(
                candidate_id=common["candidate_id"],
                gene_symbol=common["gene_symbol"],
                species=species,
                uniprot_accession=common["uniprot_accession"],
                evidence_type="uniprot_topology_features",
                query=query,
                source_name=source_name,
                failure_mode="uniprot_topology_missing",
            )
        )
    records.append(
        make_evidence_record(
            **common,
            evidence_type="uniprot_isoform_ambiguity",
            evidence_value="present" if normalized.get("isoform_ambiguity") else "not_detected",
            normalized_value="ambiguous" if normalized.get("isoform_ambiguity") else "none_detected",
            confidence="medium",
        )
    )
    return records
