#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def enum_values(schema: dict[str, Any], field: str) -> set[str]:
    return set(schema.get("properties", {}).get(field, {}).get("enum", []))


def validate_record(record: dict[str, Any], schema: dict[str, Any], line_no: int) -> list[str]:
    errors: list[str] = []
    required = schema.get("required", [])
    missing = [field for field in required if field not in record]
    if missing:
        errors.append(f"line {line_no}: missing required fields: {', '.join(missing)}")
        return errors

    if record.get("record_version") != "2.0":
        errors.append(f"line {line_no}: record_version must be 2.0")

    evidence_statuses = enum_values(schema, "evidence_status")
    if record.get("evidence_status") not in evidence_statuses:
        errors.append(f"line {line_no}: invalid evidence_status={record.get('evidence_status')!r}")

    source_levels = enum_values(schema, "source_authority_level")
    if record.get("source_authority_level") not in source_levels:
        errors.append(f"line {line_no}: invalid source_authority_level={record.get('source_authority_level')!r}")

    conflict_statuses = enum_values(schema, "conflict_status")
    if record.get("conflict_status") not in conflict_statuses:
        errors.append(f"line {line_no}: invalid conflict_status={record.get('conflict_status')!r}")

    status = record.get("evidence_status")
    if status == "missing":
        if str(record.get("evidence_value", "")).strip() or str(record.get("normalized_value", "")).strip():
            errors.append(f"line {line_no}: missing evidence must not carry evidence_value or normalized_value")
    if status == "confirmed_live":
        live_required = ["source_url", "source_version", "retrieved_at", "raw_response_sha256"]
        blank = [field for field in live_required if not str(record.get(field, "")).strip()]
        if blank:
            errors.append(f"line {line_no}: confirmed_live missing source metadata: {', '.join(blank)}")
    if status == "confirmed_local_xlsx" and "local" not in str(record.get("source_name", "")).lower():
        errors.append(f"line {line_no}: confirmed_local_xlsx must use explicit local source_name")
    if status == "confirmed_fixture" and "fixture" not in str(record.get("source_name", "")).lower():
        errors.append(f"line {line_no}: confirmed_fixture must use fixture source_name")
    if status == "conflict":
        if record.get("conflict_status") in {"none", "not_checked", ""}:
            errors.append(f"line {line_no}: conflict evidence requires conflict_status")
        if not str(record.get("failure_mode", "")).strip():
            errors.append(f"line {line_no}: conflict evidence requires failure_mode")
    return errors


def validate_jsonl(input_path: Path, schema_path: Path) -> dict[str, Any]:
    schema = load_schema(schema_path)
    errors: list[str] = []
    status_counts: dict[str, int] = {}
    records = 0
    with input_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_no}: invalid JSON: {exc.msg}")
                continue
            if not isinstance(record, dict):
                errors.append(f"line {line_no}: JSONL row must be an object")
                continue
            records += 1
            status = str(record.get("evidence_status", ""))
            status_counts[status] = status_counts.get(status, 0) + 1
            errors.extend(validate_record(record, schema, line_no))
    if records == 0:
        errors.append("no evidence records found")
    return {
        "status": "pass" if not errors else "fail",
        "input": str(input_path),
        "schema": str(schema_path),
        "record_count": records,
        "evidence_status_counts": status_counts,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate EvidenceRecord v2 JSONL output")
    parser.add_argument("--input", required=True, type=Path, help="EvidenceRecord JSONL file")
    parser.add_argument("--schema", required=True, type=Path, help="EvidenceRecord v2 schema JSON")
    args = parser.parse_args()

    if not args.input.exists():
        print(json.dumps({"status": "fail", "errors": [f"input not found: {args.input}"]}, indent=2), file=sys.stderr)
        return 2
    if not args.schema.exists():
        print(json.dumps({"status": "fail", "errors": [f"schema not found: {args.schema}"]}, indent=2), file=sys.stderr)
        return 2
    summary = validate_jsonl(args.input, args.schema)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
