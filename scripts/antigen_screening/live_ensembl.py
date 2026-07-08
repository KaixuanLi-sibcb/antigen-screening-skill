from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .evidence import compute_raw_response_sha256, make_evidence_record, missing_evidence_record


ENSEMBL_HOMOLOGY = "https://rest.ensembl.org/homology/symbol/{species}/{symbol}"
ADAPTER_NAME = "ensembl_live_orthology_adapter"
ADAPTER_VERSION = "0.5.0"


def http_json(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "antigen-screening/0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def homology_url(gene_symbol: str, species: str, target_species: str, target_taxon: str, include_sequence: bool = True) -> str:
    params = {
        "target_species": target_species,
        "target_taxon": target_taxon,
        "type": "orthologues",
    }
    if include_sequence:
        params["sequence"] = "pep"
    return (
        ENSEMBL_HOMOLOGY.format(species=urllib.parse.quote(species), symbol=urllib.parse.quote(gene_symbol))
        + "?"
        + urllib.parse.urlencode(params)
    )


def load_ensembl_source(
    *,
    gene_symbol: str,
    species: str = "human",
    target_species: str = "mouse",
    target_taxon: str = "10090",
    offline_fixture: Path | None = None,
    no_network: bool = False,
    timeout: int = 20,
) -> tuple[str, dict[str, Any] | None, dict[str, str]]:
    if offline_fixture:
        try:
            raw = json.loads(offline_fixture.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return "error", None, {"error": f"{type(exc).__name__}: {exc}", "source_name": "fixture_ensembl_homology_json"}
        return "fixture", raw, {"source_path": str(offline_fixture), "source_name": "fixture_ensembl_homology_json"}
    if no_network:
        return "missing", None, {"error": "network disabled and no offline fixture supplied", "source_name": "ensembl_live"}
    url = homology_url(gene_symbol, species, target_species, target_taxon)
    try:
        raw = http_json(url, timeout)
    except Exception as exc:  # noqa: BLE001
        return "error", None, {"error": f"{type(exc).__name__}: {exc}", "source_name": "ensembl_live", "source_url": url}
    return "live", raw, {"source_name": "ensembl_live", "source_url": url, "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def parse_orthologies(raw: dict[str, Any]) -> list[dict[str, Any]]:
    data = raw.get("data") or []
    if not data:
        return []
    homologies = data[0].get("homologies") or []
    parsed = []
    for item in homologies:
        target = item.get("target") or {}
        source = item.get("source") or data[0]
        parsed.append(
            {
                "type": str(item.get("type") or ""),
                "target_gene_id": str(target.get("id") or ""),
                "target_protein_id": str(target.get("protein_id") or target.get("protein_stable_id") or ""),
                "target_species": str(target.get("species") or ""),
                "target_gene_symbol": str(target.get("display_id") or target.get("gene_symbol") or ""),
                "target_peptide": str(target.get("align_seq") or target.get("seq") or target.get("protein_sequence") or ""),
                "source_gene_id": str(source.get("id") or ""),
                "source_protein_id": str(source.get("protein_id") or source.get("protein_stable_id") or ""),
                "source_species": str(source.get("species") or ""),
                "source_peptide": str(source.get("align_seq") or source.get("seq") or source.get("protein_sequence") or ""),
                "perc_id": str(item.get("target", {}).get("perc_id") or item.get("perc_id") or ""),
                "perc_pos": str(item.get("target", {}).get("perc_pos") or item.get("perc_pos") or ""),
            }
        )
    return parsed


def _source_fields(kind: str, metadata: dict[str, str], raw: dict[str, Any] | None) -> dict[str, str]:
    if kind == "live":
        return {
            "source_name": "ensembl_live",
            "source_authority_level": "public_database",
            "source_url": metadata.get("source_url", ""),
            "source_version": "Ensembl REST current",
            "retrieved_at": metadata.get("retrieved_at", ""),
            "raw_response_sha256": compute_raw_response_sha256(raw),
            "license_note": "Ensembl REST response; check Ensembl terms before redistribution.",
        }
    return {
        "source_name": metadata.get("source_name", "fixture_ensembl_homology_json"),
        "source_authority_level": "fixture",
        "source_url": "",
        "source_version": "fixture_v1",
        "retrieved_at": "",
        "raw_response_sha256": compute_raw_response_sha256(raw),
        "license_note": "Local Ensembl-like homology fixture for offline validation.",
    }


def ensembl_evidence_records(
    *,
    raw: dict[str, Any] | None,
    kind: str,
    metadata: dict[str, str],
    candidate_id: str,
    gene_symbol: str,
    species: str = "human",
    target_species: str = "mouse",
    target_taxon: str = "10090",
    query: dict[str, str] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    query = query or {
        "gene_symbol": gene_symbol,
        "species": species,
        "target_species": target_species,
        "target_taxon": target_taxon,
        "type": "orthologues",
    }
    if kind in {"missing", "error"} or raw is None:
        status = "error" if kind == "error" else "missing"
        source_name = metadata.get("source_name", "ensembl_live")
        authority = "fixture" if "fixture" in source_name.lower() else "public_database"
        return [
            make_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                evidence_type="ensembl_orthology_lookup",
                evidence_status=status,
                source_name=source_name,
                source_authority_level=authority,
                source_url=metadata.get("source_url", ""),
                source_version="Ensembl REST current" if authority == "public_database" else "fixture_v1",
                query=query,
                adapter_name=ADAPTER_NAME,
                adapter_version=ADAPTER_VERSION,
                confidence="none",
                failure_mode=metadata.get("error", "ensembl_orthology_unavailable"),
            )
        ], []
    orthologs = parse_orthologies(raw)
    source_fields = _source_fields(kind, metadata, raw)
    common = {
        "candidate_id": candidate_id,
        "gene_symbol": gene_symbol,
        "species": species,
        "query": query,
        "adapter_name": ADAPTER_NAME,
        "adapter_version": ADAPTER_VERSION,
        **source_fields,
    }
    if not orthologs:
        return [
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                evidence_type="ensembl_orthology_lookup",
                query=query,
                source_name=common["source_name"],
                failure_mode="no_mouse_ortholog_returned",
            )
        ], orthologs
    status = "confirmed_live" if kind == "live" else "confirmed_fixture"
    records = [
        make_evidence_record(
            **common,
            evidence_type="ensembl_orthology_lookup",
            evidence_value=orthologs[0].get("target_gene_id", ""),
            normalized_value=orthologs[0].get("target_gene_symbol") or orthologs[0].get("target_gene_id", ""),
            evidence_status=status,
            confidence="high" if len(orthologs) == 1 else "medium",
        ),
        make_evidence_record(
            **common,
            evidence_type="ensembl_ortholog_count",
            evidence_value=str(len(orthologs)),
            normalized_value=str(len(orthologs)),
            evidence_status=status,
            confidence="high",
        ),
    ]
    if len(orthologs) > 1:
        records.append(
            make_evidence_record(
                **common,
                evidence_type="ensembl_orthology_ambiguity",
                evidence_value="|".join(o.get("target_gene_id", "") for o in orthologs),
                normalized_value="multiple_orthologs",
                evidence_status="conflict",
                confidence="medium",
                conflict_status="source_conflict",
                failure_mode="multiple_mouse_ortholog_candidates",
            )
        )
    return records, orthologs
