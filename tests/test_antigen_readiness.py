from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.antigen_readiness import readiness_for_row
from antigen_screening.io import CANDIDATE_OUTPUT_COLUMNS, read_tsv, write_tsv


def row(**updates: str) -> dict[str, str]:
    base = {column: "" for column in CANDIDATE_OUTPUT_COLUMNS}
    base.update(
        {
            "candidate_id": "C1",
            "gene_symbol": "TEST",
            "modality": "antibody",
            "antigen_accessibility": "surface_single_pass",
            "accessibility_gate": "pass",
            "ecd_region": "20-260",
            "ecd_length": "241",
            "ecd_evidence_state": "confirmed",
            "constructability_gate": "pass",
            "constructability_class": "soluble_ecd_construct",
            "isoform_risk": "none_detected",
        }
    )
    base.update(updates)
    return base


class AntigenReadinessTest(unittest.TestCase):
    def test_clean_soluble_ecd_is_ready(self) -> None:
        result = readiness_for_row(row())
        self.assertEqual(result["antigen_readiness"], "ready")
        self.assertEqual(result["primary_screening_material"], "soluble_ecd")

    def test_multi_pass_uses_cell_display_fallback(self) -> None:
        result = readiness_for_row(
            row(
                antigen_accessibility="surface_multi_pass",
                ecd_region="missing_or_discontinuous",
                ecd_evidence_state="missing",
                constructability_gate="partial",
            )
        )
        self.assertEqual(result["antigen_readiness"], "conditional")
        self.assertIn("cell_display_fallback", result["readiness_flags"])
        self.assertEqual(result["primary_screening_material"], "full_length_cell_display")

    def test_secreted_car_candidate_is_conditional_not_surface_ready(self) -> None:
        result = readiness_for_row(
            row(
                gene_symbol="ALB",
                modality="car_t",
                antigen_accessibility="secreted",
                ecd_length="585",
                constructability_gate="partial",
            )
        )
        self.assertEqual(result["antigen_readiness"], "conditional")
        self.assertIn("secreted_soluble_antigen", result["readiness_flags"])

    def test_intracellular_marker_is_not_ready(self) -> None:
        result = readiness_for_row(
            row(
                gene_symbol="MKI67",
                antigen_accessibility="intracellular_or_nuclear",
                accessibility_gate="fail",
                ecd_region="not_applicable",
                ecd_length="",
                constructability_gate="fail",
            )
        )
        self.assertEqual(result["antigen_readiness"], "not_ready")
        self.assertEqual(result["primary_screening_material"], "not_recommended")

    def test_short_long_gpi_and_expression_risks_are_flagged(self) -> None:
        short = readiness_for_row(row(ecd_length="80"))
        self.assertIn("short_ecd", short["readiness_flags"])
        long = readiness_for_row(row(ecd_length="650"))
        self.assertIn("long_ecd", long["readiness_flags"])
        gpi = readiness_for_row(row(antigen_accessibility="gpi_anchored"))
        self.assertIn("gpi_anchor", gpi["readiness_flags"])
        risky = readiness_for_row(row(ecd_notes="cysteine rich disulfide glycosylation", isoform_risk="isoform_changes_tm"))
        self.assertIn("cysteine_disulfide_risk", risky["readiness_flags"])
        self.assertIn("glycosylation_risk", risky["readiness_flags"])
        self.assertIn("isoform_ambiguity", risky["readiness_flags"])

    def test_cli_writes_readiness_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "antigen_screening_table.tsv"
            outdir = Path(tmp) / "readiness"
            write_tsv(input_path, [row(), row(gene_symbol="MKI67", antigen_accessibility="intracellular_or_nuclear", accessibility_gate="fail")], CANDIDATE_OUTPUT_COLUMNS)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "run_antigen_readiness.py"), "--input", str(input_path), "--outdir", str(outdir)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            output = read_tsv(outdir / "antigen_readiness_table.tsv")
            self.assertEqual(len(output), 2)
            self.assertTrue((outdir / "antigen_readiness_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
