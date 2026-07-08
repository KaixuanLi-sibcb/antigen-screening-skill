from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.hpa_adapter import load_hpa_source, normalize_hpa_record, run_hpa_normal_tissue_risk, summarize_hpa_risk
from antigen_screening.io import CANDIDATE_OUTPUT_COLUMNS, read_tsv, write_tsv
from validate_evidence_records import validate_jsonl


FIXTURES = ROOT / "tests" / "fixtures" / "hpa"
SCHEMA = ROOT / "schemas" / "evidence_record.schema.json"


def candidate(gene: str) -> dict[str, str]:
    row = {column: "" for column in CANDIDATE_OUTPUT_COLUMNS}
    row.update({"candidate_id": gene, "gene_symbol": gene, "species": "human"})
    return row


class HpaAdapterTest(unittest.TestCase):
    def test_protein_high_risk_tissue_drives_high_risk(self) -> None:
        kind, raw, _ = load_hpa_source(gene_symbol="ALB", fixtures_dir=FIXTURES, offline=True)
        self.assertEqual(kind, "fixture")
        summary = summarize_hpa_risk(normalize_hpa_record(raw, "ALB"))
        self.assertEqual(summary["normal_tissue_risk"], "high")
        self.assertIn("liver", summary["high_risk_tissue_flags"])

    def test_rna_and_protein_are_separate_and_blank_is_missing(self) -> None:
        kind, raw, _ = load_hpa_source(gene_symbol="MKI67", fixtures_dir=FIXTURES, offline=True)
        self.assertEqual(kind, "fixture")
        summary = summarize_hpa_risk(normalize_hpa_record(raw, "MKI67"))
        self.assertEqual(summary["normal_tissue_risk"], "unknown")
        self.assertEqual(summary["rna_evidence_level"], "missing")
        self.assertEqual(summary["protein_evidence_level"], "missing")

    def test_missing_fixture_is_missing_not_low(self) -> None:
        kind, raw, metadata = load_hpa_source(gene_symbol="NOPE", fixtures_dir=FIXTURES, offline=True)
        self.assertEqual(kind, "missing")
        summary = summarize_hpa_risk(normalize_hpa_record(raw, "NOPE"))
        self.assertEqual(summary["normal_tissue_risk"], "unknown")
        self.assertIn("missing", metadata["error"])

    def test_runner_writes_outputs_and_valid_evidence_v2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "candidates.tsv"
            outdir = Path(tmp) / "hpa"
            write_tsv(input_path, [candidate("PDCD1"), candidate("CD19"), candidate("ALB"), candidate("MKI67")], CANDIDATE_OUTPUT_COLUMNS)
            summary = run_hpa_normal_tissue_risk(input_path=input_path, outdir=outdir, fixtures_dir=FIXTURES, offline=True)
            self.assertEqual(summary["status"], "pass")
            rows = read_tsv(outdir / "normal_tissue_risk.tsv")
            self.assertEqual(len(rows), 4)
            validation = validate_jsonl(outdir / "hpa_evidence_records.jsonl", SCHEMA)
            self.assertEqual(validation["status"], "pass")

    def test_cli_fixture_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "candidates.tsv"
            outdir = Path(tmp) / "hpa"
            write_tsv(input_path, [candidate("ALB")], CANDIDATE_OUTPUT_COLUMNS)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_hpa_normal_tissue_risk.py"),
                    "--input",
                    str(input_path),
                    "--outdir",
                    str(outdir),
                    "--fixtures-dir",
                    str(FIXTURES),
                    "--offline",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((outdir / "normal_tissue_risk_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
