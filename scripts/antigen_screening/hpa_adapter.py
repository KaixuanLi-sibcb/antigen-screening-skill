from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from .evidence import compute_raw_response_sha256, make_evidence_record, missing_evidence_record
from .io import read_tsv, write_jsonl, write_tsv


ADAPTER_NAME = "hpa_normal_tissue_adapter"
ADAPTER_VERSION = "0.6.0"
HPA_SEARCH_URL = "https://www.proteinatlas.org/search/{gene}.json"

NORMAL_TISSUE_COLUMNS = [
    "candidate_id",
    "gene_symbol",
    "normal_tissue_risk",
    "risk_score",
    "high_risk_tissue_flags",
    "rna_evidence_level",
    "protein_evidence_level",
    "rna_high_risk_tissues",
    "protein_high_risk_tissues",
    "evidence_status",
    "risk_rationale",
    "missing_evidence",
]

HIGH_RISK_TISSUES = {
    "heart": ("heart", "cardiac"),
    "cns": ("brain", "cns", "central nervous", "spinal cord"),
    "lung": ("lung", "bronch", "alveolar"),
    "kidney": ("kidney", "renal"),
    "liver": ("liver", "hepatic"),
    "endothelium": ("endothelium", "endothelial", "vessel", "vascular"),
    "bone_marrow": ("bone marrow", "hematopoietic", "haematopoietic", "marrow"),
    "immune_progenitor": ("progenitor", "stem cell", "b cell", "t cell", "lymphocyte", "myeloid"),
}

LEVEL_SCORES = {
    "not detected": 0,
    "none": 0,
    "negative": 0,
    "low": 1,
    "medium": 2,
    "moderate": 2,
    "high": 3,
    "strong": 3,
}


def _level_score(level: object) -> int | None:
    text = str(level or "").strip().lower()
    if not text:
        return None
    if text in LEVEL_SCORES:
        return LEVEL_SCORES[text]
    try:
        value = float(text)
    except ValueError:
        return None
    if value <= 0:
        return 0
    if value < 1:
        return 1
    if value < 10:
        return 2
    return 3


def _risk_flags_for_tissue(tissue: object) -> list[str]:
    text = str(tissue or "").lower()
    flags = []
    for flag, terms in HIGH_RISK_TISSUES.items():
        if any(term in text for term in terms):
            flags.append(flag)
    return flags


def _source_fields(kind: str, metadata: dict[str, str], raw: dict[str, Any] | None) -> dict[str, str]:
    if kind == "live":
        return {
            "source_name": "hpa_live",
            "source_authority_level": "public_database",
            "source_url": metadata.get("source_url", ""),
            "source_version": "HPA current",
            "retrieved_at": metadata.get("retrieved_at", ""),
            "raw_response_sha256": compute_raw_response_sha256(raw),
            "license_note": "HPA live response; check Human Protein Atlas terms before redistribution.",
        }
    return {
        "source_name": metadata.get("source_name", "fixture_hpa_json"),
        "source_authority_level": "fixture",
        "source_url": "",
        "source_version": "fixture_v1",
        "retrieved_at": "",
        "raw_response_sha256": compute_raw_response_sha256(raw),
        "license_note": "Local HPA-like fixture for offline normal-tissue risk validation.",
    }


def load_hpa_source(
    *,
    gene_symbol: str,
    fixtures_dir: Path | None = None,
    offline: bool = True,
    timeout: int = 20,
) -> tuple[str, dict[str, Any] | None, dict[str, str]]:
    fixture_path = fixtures_dir / f"{gene_symbol.upper()}.json" if fixtures_dir else None
    if fixture_path and fixture_path.exists():
        try:
            return "fixture", json.loads(fixture_path.read_text(encoding="utf-8")), {
                "source_name": "fixture_hpa_json",
                "source_path": str(fixture_path),
            }
        except Exception as exc:  # noqa: BLE001
            return "error", None, {"source_name": "fixture_hpa_json", "error": f"{type(exc).__name__}: {exc}"}
    if offline:
        return "missing", None, {"source_name": "fixture_hpa_json", "error": "offline fixture missing"}
    url = HPA_SEARCH_URL.format(gene=urllib.parse.quote(gene_symbol))
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "antigen-screening/0.6"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return "error", None, {"source_name": "hpa_live", "source_url": url, "error": f"{type(exc).__name__}: {exc}"}
    return "live", raw, {
        "source_name": "hpa_live",
        "source_url": url,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def normalize_hpa_record(raw: dict[str, Any] | None, gene_symbol: str) -> dict[str, Any]:
    if raw is None:
        return {"gene_symbol": gene_symbol.upper(), "rna": [], "protein": []}
    return {
        "gene_symbol": str(raw.get("gene_symbol") or raw.get("Gene") or gene_symbol).upper(),
        "rna": list(raw.get("rna") or raw.get("rna_tissue") or []),
        "protein": list(raw.get("protein") or raw.get("protein_tissue") or []),
    }


def summarize_hpa_risk(record: dict[str, Any]) -> dict[str, str]:
    rna_rows = record.get("rna") or []
    protein_rows = record.get("protein") or []
    rna_high: list[str] = []
    protein_high: list[str] = []
    flags: list[str] = []
    max_rna_score: int | None = None
    max_protein_score: int | None = None

    for item in rna_rows:
        score = _level_score(item.get("level", item.get("nTPM", item.get("value", ""))))
        if score is None:
            continue
        max_rna_score = score if max_rna_score is None else max(max_rna_score, score)
        tissue_flags = _risk_flags_for_tissue(item.get("tissue", ""))
        if tissue_flags and score >= 2:
            rna_high.append(str(item.get("tissue", "")))
            flags.extend(tissue_flags)

    for item in protein_rows:
        score = _level_score(item.get("level", item.get("value", "")))
        if score is None:
            continue
        max_protein_score = score if max_protein_score is None else max(max_protein_score, score)
        tissue_flags = _risk_flags_for_tissue(item.get("tissue", ""))
        if tissue_flags and score >= 1:
            protein_high.append(str(item.get("tissue", "")))
            flags.extend(tissue_flags)

    if max_rna_score is None and max_protein_score is None:
        risk = "unknown"
        score_text = ""
        status = "missing"
        rationale = "HPA RNA/protein values are missing or blank"
        missing = "hpa_rna;hpa_protein"
    elif protein_high:
        strongest = max_protein_score or 0
        risk = "high" if strongest >= 2 else "medium"
        score_text = str(70 + strongest * 10)
        status = "confirmed"
        rationale = "protein-level expression detected in high-risk normal tissue"
        missing = "" if max_rna_score is not None else "hpa_rna"
    elif rna_high:
        risk = "medium"
        score_text = "55"
        status = "inferred"
        rationale = "RNA expression detected in high-risk tissue without matching protein-level evidence"
        missing = "" if max_protein_score is not None else "hpa_protein"
    elif max_protein_score is not None or max_rna_score is not None:
        risk = "low"
        score_text = "20"
        status = "confirmed" if max_protein_score is not None else "inferred"
        rationale = "fixture evidence did not show expression in configured high-risk tissues"
        missing = "" if max_protein_score is not None and max_rna_score is not None else "hpa_protein" if max_protein_score is None else "hpa_rna"
    else:
        risk = "unknown"
        score_text = ""
        status = "missing"
        rationale = "HPA evidence unavailable"
        missing = "hpa_rna;hpa_protein"

    return {
        "normal_tissue_risk": risk,
        "risk_score": score_text,
        "high_risk_tissue_flags": ";".join(sorted(set(flags))),
        "rna_evidence_level": "missing" if max_rna_score is None else str(max_rna_score),
        "protein_evidence_level": "missing" if max_protein_score is None else str(max_protein_score),
        "rna_high_risk_tissues": ";".join(sorted(set(t for t in rna_high if t))),
        "protein_high_risk_tissues": ";".join(sorted(set(t for t in protein_high if t))),
        "evidence_status": status,
        "risk_rationale": rationale,
        "missing_evidence": missing,
    }


def hpa_evidence_records(
    *,
    candidate_id: str,
    gene_symbol: str,
    species: str,
    raw: dict[str, Any] | None,
    kind: str,
    metadata: dict[str, str],
    summary: dict[str, str],
) -> list[dict[str, str]]:
    query = {"gene_symbol": gene_symbol, "species": species}
    if kind in {"missing", "error"} or raw is None:
        status = "error" if kind == "error" else "missing"
        return [
            make_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                evidence_type="hpa_normal_tissue_lookup",
                evidence_status=status,
                source_name=metadata.get("source_name", "fixture_hpa_json"),
                source_authority_level="fixture" if metadata.get("source_name", "").startswith("fixture") else "public_database",
                query=query,
                adapter_name=ADAPTER_NAME,
                adapter_version=ADAPTER_VERSION,
                confidence="none",
                failure_mode=metadata.get("error", "hpa_evidence_unavailable"),
            )
        ]
    source = _source_fields(kind, metadata, raw)
    evidence_status = "confirmed_live" if kind == "live" else "confirmed_fixture"
    common = {
        "candidate_id": candidate_id,
        "gene_symbol": gene_symbol,
        "species": species,
        "query": query,
        "adapter_name": ADAPTER_NAME,
        "adapter_version": ADAPTER_VERSION,
        "evidence_status": evidence_status,
        **source,
    }
    records = []
    if summary["rna_evidence_level"] == "missing":
        records.append(
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                evidence_type="hpa_rna_tissue_expression",
                query=query,
                source_name=source["source_name"],
                failure_mode="hpa_rna_missing_or_blank",
            )
        )
    else:
        records.append(
            make_evidence_record(
                **common,
                evidence_type="hpa_rna_tissue_expression",
                evidence_value=summary["rna_high_risk_tissues"] or summary["rna_evidence_level"],
                normalized_value=summary["rna_evidence_level"],
                confidence="medium",
            )
        )
    if summary["protein_evidence_level"] == "missing":
        records.append(
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                evidence_type="hpa_protein_tissue_expression",
                query=query,
                source_name=source["source_name"],
                failure_mode="hpa_protein_missing_or_blank",
            )
        )
    else:
        records.append(
            make_evidence_record(
                **common,
                evidence_type="hpa_protein_tissue_expression",
                evidence_value=summary["protein_high_risk_tissues"] or summary["protein_evidence_level"],
                normalized_value=summary["protein_evidence_level"],
                confidence="medium",
            )
        )
    records.append(
        make_evidence_record(
            **common,
            evidence_type="hpa_normal_tissue_risk",
            evidence_value=summary["normal_tissue_risk"],
            normalized_value=summary["high_risk_tissue_flags"],
            confidence="medium" if summary["normal_tissue_risk"] != "unknown" else "none",
        )
    )
    return records


def run_hpa_normal_tissue_risk(
    *,
    input_path: Path,
    outdir: Path,
    fixtures_dir: Path | None = None,
    offline: bool = True,
    timeout: int = 20,
) -> dict[str, Any]:
    rows = read_tsv(input_path)
    risk_rows: list[dict[str, str]] = []
    evidence_rows: list[dict[str, str]] = []
    for row in rows:
        gene = (row.get("gene_symbol") or row.get("input_name") or row.get("target") or "").strip().upper()
        candidate_id = row.get("candidate_id") or gene
        species = row.get("species") or "human"
        kind, raw, metadata = load_hpa_source(gene_symbol=gene, fixtures_dir=fixtures_dir, offline=offline, timeout=timeout)
        normalized = normalize_hpa_record(raw, gene)
        summary = summarize_hpa_risk(normalized)
        risk_row = {
            "candidate_id": candidate_id,
            "gene_symbol": gene,
            **summary,
        }
        risk_rows.append(risk_row)
        evidence_rows.extend(
            hpa_evidence_records(
                candidate_id=candidate_id,
                gene_symbol=gene,
                species=species,
                raw=raw,
                kind=kind,
                metadata=metadata,
                summary=summary,
            )
        )
    outdir.mkdir(parents=True, exist_ok=True)
    write_tsv(outdir / "normal_tissue_risk.tsv", risk_rows, NORMAL_TISSUE_COLUMNS)
    write_jsonl(outdir / "hpa_evidence_records.jsonl", evidence_rows)
    summary_out = {
        "status": "pass",
        "input": str(input_path),
        "outdir": str(outdir),
        "candidate_count": len(risk_rows),
        "risk_counts": dict(Counter(row["normal_tissue_risk"] for row in risk_rows)),
        "evidence_record_count": len(evidence_rows),
        "outputs": {
            "normal_tissue_risk": str(outdir / "normal_tissue_risk.tsv"),
            "hpa_evidence_records": str(outdir / "hpa_evidence_records.jsonl"),
            "normal_tissue_risk_summary": str(outdir / "normal_tissue_risk_summary.json"),
        },
    }
    (outdir / "normal_tissue_risk_summary.json").write_text(
        json.dumps(summary_out, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary_out
