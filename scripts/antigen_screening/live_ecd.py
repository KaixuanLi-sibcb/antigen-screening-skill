from __future__ import annotations

from typing import Any

from .ecd import extract_ecd
from .evidence import make_evidence_record, missing_evidence_record
from .topology import classify_accessibility


ADAPTER_NAME = "live_ecd_validation_adapter"
ADAPTER_VERSION = "0.5.0"


def parse_identity_fraction(value: object) -> float | None:
    text = str(value or "").strip().replace("%", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if parsed > 1:
        parsed /= 100.0
    return parsed if parsed >= 0 else None


def parse_region(region: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for chunk in str(region or "").replace(",", ";").split(";"):
        chunk = chunk.strip()
        if not chunk or "-" not in chunk:
            continue
        start_text, end_text = chunk.split("-", 1)
        try:
            start = int(start_text)
            end = int(end_text)
        except ValueError:
            continue
        if start > 0 and end >= start:
            ranges.append((start, end))
    return ranges


def protein_letters(sequence: str, keep_gaps: bool = False) -> str:
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    if keep_gaps:
        allowed.add("-")
    return "".join(ch for ch in str(sequence or "").upper() if ch in allowed)


def extract_by_ranges(sequence: str, ranges: list[tuple[int, int]]) -> str:
    clean = protein_letters(sequence)
    pieces = []
    for start, end in ranges:
        pieces.append(clean[start - 1 : end])
    return "".join(pieces)


def aligned_columns_for_ranges(source_alignment: str, ranges: list[tuple[int, int]]) -> list[int]:
    wanted = set()
    for start, end in ranges:
        wanted.update(range(start, end + 1))
    columns: list[int] = []
    residue_pos = 0
    for idx, char in enumerate(protein_letters(source_alignment, keep_gaps=True)):
        if char == "-":
            continue
        residue_pos += 1
        if residue_pos in wanted:
            columns.append(idx)
    return columns


def extract_target_by_source_ranges(source_alignment: str, target_alignment: str, ranges: list[tuple[int, int]]) -> str:
    columns = aligned_columns_for_ranges(source_alignment, ranges)
    target = protein_letters(target_alignment, keep_gaps=True)
    residues = []
    for column in columns:
        if column < len(target):
            residue = target[column]
            if residue != "-":
                residues.append(residue)
    return "".join(residues)


def pairwise_identity(sequence_a: str, sequence_b: str) -> float | None:
    a = protein_letters(sequence_a)
    b = protein_letters(sequence_b)
    if not a or not b:
        return None
    if len(a) == len(b):
        return sum(1 for left, right in zip(a, b) if left == right) / len(a)
    aligned_a, aligned_b = _needleman_wunsch(a, b)
    denominator = sum(1 for left, right in zip(aligned_a, aligned_b) if left != "-" or right != "-")
    if denominator == 0:
        return None
    matches = sum(1 for left, right in zip(aligned_a, aligned_b) if left == right and left != "-")
    return matches / denominator


def _needleman_wunsch(a: str, b: str) -> tuple[str, str]:
    match_score = 1
    mismatch_score = 0
    gap_score = -1
    rows = len(a) + 1
    cols = len(b) + 1
    score = [[0] * cols for _ in range(rows)]
    trace = [[""] * cols for _ in range(rows)]
    for i in range(1, rows):
        score[i][0] = i * gap_score
        trace[i][0] = "up"
    for j in range(1, cols):
        score[0][j] = j * gap_score
        trace[0][j] = "left"
    for i in range(1, rows):
        for j in range(1, cols):
            diag = score[i - 1][j - 1] + (match_score if a[i - 1] == b[j - 1] else mismatch_score)
            up = score[i - 1][j] + gap_score
            left = score[i][j - 1] + gap_score
            best = max(diag, up, left)
            score[i][j] = best
            trace[i][j] = "diag" if best == diag else "up" if best == up else "left"
    i = len(a)
    j = len(b)
    out_a: list[str] = []
    out_b: list[str] = []
    while i > 0 or j > 0:
        move = trace[i][j]
        if i > 0 and j > 0 and (move == "diag" or not move):
            out_a.append(a[i - 1])
            out_b.append(b[j - 1])
            i -= 1
            j -= 1
        elif i > 0 and (move == "up" or j == 0):
            out_a.append(a[i - 1])
            out_b.append("-")
            i -= 1
        else:
            out_a.append("-")
            out_b.append(b[j - 1])
            j -= 1
    return "".join(reversed(out_a)), "".join(reversed(out_b))


def computed_source_fields(source_kind: str) -> dict[str, str]:
    if source_kind == "live":
        return {
            "evidence_status": "inferred_live",
            "source_name": "computed_live_ecd_validation",
            "source_authority_level": "computed",
            "source_version": "UniProtKB REST current + Ensembl REST current",
            "license_note": "Computed from live UniProt/Ensembl values; check source database terms before redistribution.",
        }
    return {
        "evidence_status": "confirmed_fixture",
        "source_name": "fixture_computed_ecd_validation",
        "source_authority_level": "computed",
        "source_version": "fixture_v1",
        "license_note": "Computed from local live-validation fixtures for offline validation.",
    }


def validate_ecd_identity(
    *,
    human_record: dict[str, Any] | None,
    ortholog: dict[str, Any] | None,
    candidate_id: str,
    gene_symbol: str,
    species: str = "human",
    uniprot_accession: str = "",
    local_ecd_identity: str = "",
    tolerance: float = 0.05,
    source_kind: str = "fixture",
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    query = {
        "candidate_id": candidate_id,
        "gene_symbol": gene_symbol,
        "tolerance": tolerance,
        "source_kind": source_kind,
    }
    common = {
        "candidate_id": candidate_id,
        "gene_symbol": gene_symbol,
        "species": species,
        "uniprot_accession": uniprot_accession or (human_record or {}).get("accession", ""),
        "query": query,
        "adapter_name": ADAPTER_NAME,
        "adapter_version": ADAPTER_VERSION,
        **computed_source_fields(source_kind),
    }
    records: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    summary: dict[str, Any] = {
        "candidate_id": candidate_id,
        "gene_symbol": gene_symbol,
        "status": "pass",
        "human_ecd_region": "",
        "human_ecd_length": 0,
        "mouse_ecd_length": 0,
        "computed_ecd_identity": "",
        "local_ecd_identity": local_ecd_identity,
        "identity_difference": "",
        "conflict_count": 0,
        "errors": [],
    }
    if not human_record:
        records.append(
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                uniprot_accession=common["uniprot_accession"],
                evidence_type="live_human_ecd_boundary",
                query=query,
                source_name=common["source_name"],
                failure_mode="human_uniprot_record_missing",
            )
        )
        summary["status"] = "missing"
        summary["errors"].append("human_uniprot_record_missing")
        return summary, records, conflicts

    topology = classify_accessibility(human_record)
    ecd = extract_ecd(human_record, topology)
    ranges = parse_region(ecd.get("ecd_region", ""))
    if not ranges or ecd.get("ecd_evidence_state") in {"missing", "not_applicable"}:
        records.append(
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                uniprot_accession=common["uniprot_accession"],
                evidence_type="live_human_ecd_boundary",
                query=query,
                source_name=common["source_name"],
                failure_mode=ecd.get("ecd_notes") or "human_ecd_boundary_missing",
            )
        )
        summary["status"] = "missing"
        summary["errors"].append("human_ecd_boundary_missing")
        return summary, records, conflicts

    human_sequence = str(human_record.get("sequence") or "")
    human_ecd = extract_by_ranges(human_sequence, ranges)
    summary["human_ecd_region"] = ecd["ecd_region"]
    summary["human_ecd_length"] = len(human_ecd)
    records.append(
        make_evidence_record(
            **common,
            evidence_type="live_human_ecd_boundary",
            evidence_value=ecd["ecd_region"],
            normalized_value=str(len(human_ecd)),
            confidence=ecd.get("ecd_boundary_confidence", "medium"),
        )
    )
    if not human_ecd:
        records.append(
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                uniprot_accession=common["uniprot_accession"],
                evidence_type="live_human_ecd_sequence",
                query=query,
                source_name=common["source_name"],
                failure_mode="human_ecd_sequence_empty",
            )
        )
        summary["status"] = "missing"
        summary["errors"].append("human_ecd_sequence_empty")
        return summary, records, conflicts
    records.append(
        make_evidence_record(
            **common,
            evidence_type="live_human_ecd_sequence_length",
            evidence_value=str(len(human_ecd)),
            normalized_value=str(len(human_ecd)),
            confidence="high",
        )
    )

    if not ortholog:
        records.append(
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                uniprot_accession=common["uniprot_accession"],
                evidence_type="live_mouse_ecd_sequence",
                query=query,
                source_name=common["source_name"],
                failure_mode="mouse_ortholog_record_missing",
            )
        )
        summary["status"] = "missing"
        summary["errors"].append("mouse_ortholog_record_missing")
        return summary, records, conflicts

    source_alignment = str(ortholog.get("source_peptide") or human_sequence)
    target_alignment = str(ortholog.get("target_peptide") or "")
    mouse_ecd = extract_target_by_source_ranges(source_alignment, target_alignment, ranges)
    summary["mouse_ecd_length"] = len(mouse_ecd)
    if not mouse_ecd:
        records.append(
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                uniprot_accession=common["uniprot_accession"],
                evidence_type="live_mouse_ecd_sequence",
                query=query,
                source_name=common["source_name"],
                failure_mode="mouse_ecd_sequence_empty",
            )
        )
        summary["status"] = "missing"
        summary["errors"].append("mouse_ecd_sequence_empty")
        return summary, records, conflicts
    records.append(
        make_evidence_record(
            **common,
            evidence_type="live_mouse_ecd_sequence_length",
            evidence_value=str(len(mouse_ecd)),
            normalized_value=str(len(mouse_ecd)),
            confidence="medium",
        )
    )

    identity = pairwise_identity(human_ecd, mouse_ecd)
    if identity is None:
        records.append(
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                uniprot_accession=common["uniprot_accession"],
                evidence_type="live_computed_ecd_identity",
                query=query,
                source_name=common["source_name"],
                failure_mode="ecd_pairwise_identity_unavailable",
            )
        )
        summary["status"] = "missing"
        summary["errors"].append("ecd_pairwise_identity_unavailable")
        return summary, records, conflicts

    computed_text = f"{identity:.6f}"
    summary["computed_ecd_identity"] = computed_text
    records.append(
        make_evidence_record(
            **common,
            evidence_type="live_computed_ecd_identity",
            evidence_value=computed_text,
            normalized_value=computed_text,
            confidence="medium",
        )
    )
    local_identity = parse_identity_fraction(local_ecd_identity)
    if local_identity is None:
        records.append(
            missing_evidence_record(
                candidate_id=candidate_id,
                gene_symbol=gene_symbol,
                species=species,
                uniprot_accession=common["uniprot_accession"],
                evidence_type="local_tabular_ecd_identity",
                query=query,
                source_name="local_tabular_ecd_identity",
                failure_mode="local_ecd_identity_missing",
            )
        )
        return summary, records, conflicts

    local_text = f"{local_identity:.6f}"
    summary["local_ecd_identity"] = local_text
    records.append(
        make_evidence_record(
            candidate_id=candidate_id,
            gene_symbol=gene_symbol,
            species=species,
            uniprot_accession=common["uniprot_accession"],
            evidence_type="local_tabular_ecd_identity",
            evidence_value=local_text,
            normalized_value=local_text,
            evidence_status="confirmed_local_xlsx",
            source_name="local_tabular_ecd_identity",
            source_authority_level="local_lab",
            query=query,
            adapter_name=ADAPTER_NAME,
            adapter_version=ADAPTER_VERSION,
            confidence="medium",
            license_note="Local user-provided value; private source files remain outside Git.",
        )
    )
    diff = abs(identity - local_identity)
    summary["identity_difference"] = f"{diff:.6f}"
    if diff > tolerance:
        conflict_common = dict(common)
        conflict_common.pop("evidence_status", None)
        conflict = {
            "candidate_id": candidate_id,
            "gene_symbol": gene_symbol,
            "conflict_type": "ecd_identity_local_vs_computed",
            "local_value": local_text,
            "computed_value": computed_text,
            "difference": f"{diff:.6f}",
            "tolerance": f"{tolerance:.6f}",
            "failure_mode": "local_tabular_ecd_identity_differs_from_computed",
        }
        conflicts.append(conflict)
        records.append(
            make_evidence_record(
                **conflict_common,
                evidence_type="ecd_identity_local_vs_computed",
                evidence_value=f"local={local_text};computed={computed_text}",
                normalized_value=f"diff={diff:.6f}",
                evidence_status="conflict",
                confidence="medium",
                conflict_status="value_conflict",
                failure_mode=conflict["failure_mode"],
            )
        )
        summary["status"] = "conflict"
        summary["conflict_count"] = 1
    else:
        records.append(
            make_evidence_record(
                **common,
                evidence_type="ecd_identity_local_vs_computed",
                evidence_value=f"local={local_text};computed={computed_text}",
                normalized_value="within_tolerance",
                confidence="medium",
            )
        )
    return summary, records, conflicts
