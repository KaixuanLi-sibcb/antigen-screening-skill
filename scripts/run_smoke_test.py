#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str]) -> dict[str, str]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {"cmd": " ".join(cmd), "returncode": str(proc.returncode), "stdout": proc.stdout, "stderr": proc.stderr}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter="\t")]


def require_columns(path: Path, columns: list[str], errors: list[str]) -> None:
    rows = read_tsv(path)
    if not rows:
        errors.append(f"{path.name} has no data rows")
        return
    missing = [col for col in columns if col not in rows[0]]
    if missing:
        errors.append(f"{path.name} missing columns: {', '.join(missing)}")


def sanity_checks(outdir: Path) -> list[str]:
    errors: list[str] = []
    screening = {row["gene_symbol"]: row for row in read_tsv(outdir / "antigen_screening_table.tsv")}
    constructs = {row["gene_symbol"]: row for row in read_tsv(outdir / "construct_plan.tsv")}

    pdcd1 = screening.get("PDCD1", {})
    if pdcd1.get("accessibility_gate") != "pass" or pdcd1.get("antigen_accessibility") == "intracellular_or_nuclear":
        errors.append("PDCD1 should be membrane-accessible and not intracellular fail")

    cd19 = screening.get("CD19", {})
    if cd19.get("accessibility_gate") != "pass" or constructs.get("CD19", {}).get("construct_recommendation") in {"", "no_construct"}:
        errors.append("CD19 should be membrane-accessible with a plausible construct plan")

    alb = screening.get("ALB", {})
    if alb.get("antigen_accessibility") != "secreted":
        errors.append("ALB should be classified as secreted")
    if alb.get("modality_gate") != "fail" or "secreted_not_cell_surface" not in alb.get("risk_flags", ""):
        errors.append("ALB CAR-T row should be flagged as not a transmembrane cell-surface CAR target")

    mki67 = screening.get("MKI67", {})
    if mki67.get("accessibility_gate") != "fail" or mki67.get("antigen_accessibility") != "intracellular_or_nuclear":
        errors.append("MKI67 must fail surface antigen accessibility")
    if constructs.get("MKI67", {}).get("construct_recommendation") != "no_construct":
        errors.append("MKI67 must not receive an ECD construct")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline smoke test for antigen-screening skill")
    parser.add_argument("--skill-dir", required=True, type=Path)
    parser.add_argument("--outdir", type=Path, help="Output directory")
    args = parser.parse_args()

    skill_dir = args.skill_dir.resolve()
    outdir = args.outdir.resolve() if args.outdir else Path(tempfile.mkdtemp(prefix="antigen_smoke_"))
    fixtures = skill_dir / "tests" / "fixtures"
    candidate_input = fixtures / "candidate_input.tsv"
    errors: list[str] = []
    commands: list[dict[str, str]] = []

    outdir.mkdir(parents=True, exist_ok=True)
    commands.append(
        run(
            [
                sys.executable,
                str(skill_dir / "scripts" / "score_antigen_candidates.py"),
                "--input",
                str(candidate_input),
                "--fixtures-dir",
                str(fixtures),
                "--outdir",
                str(outdir),
                "--offline",
                "--species",
                "human",
                "--ecd-identity-threshold",
                "0.70",
                "--mouse-model",
            ]
        )
    )
    commands.append(
        run(
            [
                sys.executable,
                str(skill_dir / "scripts" / "make_construct_plan.py"),
                "--input",
                str(outdir / "antigen_screening_table.tsv"),
                "--outdir",
                str(outdir),
            ]
        )
    )

    for command in commands:
        if command["returncode"] != "0":
            errors.append(f"command failed: {command['cmd']}\n{command['stderr']}")

    required_files = [
        "antigen_screening_table.tsv",
        "evidence_records.jsonl",
        "evidence_conflicts.tsv",
        "evidence_conflict_summary.json",
        "risk_flags.tsv",
        "construct_plan.tsv",
        "report.md",
    ]
    for name in required_files:
        path = outdir / name
        if not path.exists():
            errors.append(f"missing output file: {name}")
        elif path.stat().st_size == 0:
            errors.append(f"empty output file: {name}")

    if not errors:
        require_columns(outdir / "antigen_screening_table.tsv", ["gene_symbol", "accessibility_gate", "modality_gate", "priority_call"], errors)
        require_columns(outdir / "construct_plan.tsv", ["gene_symbol", "construct_recommendation", "stop_condition"], errors)
        require_columns(outdir / "risk_flags.tsv", ["gene_symbol", "flag_type", "severity", "action"], errors)
        errors.extend(sanity_checks(outdir))

    status = "pass" if not errors else "fail"
    summary = {
        "status": status,
        "skill_dir": str(skill_dir),
        "outdir": str(outdir),
        "offline": True,
        "commands": commands,
        "errors": errors,
    }
    (outdir / "smoke_test_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report_lines = [
        "# Smoke Test Report",
        "",
        f"Status: {status}",
        f"Skill dir: {skill_dir}",
        f"Output dir: {outdir}",
        "Mode: offline fixture",
        "",
        "## Sanity Cases",
        "- PDCD1: membrane-accessible, not intracellular fail.",
        "- CD19: membrane-accessible, construct plausible.",
        "- ALB: secreted protein, flagged as not CAR-T cell-surface target.",
        "- MKI67: nuclear/intracellular marker, surface accessibility fail and no construct.",
        "",
        "## Errors",
    ]
    report_lines.extend([f"- {error}" for error in errors] or ["- none"])
    (outdir / "smoke_test_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "outdir": str(outdir), "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
