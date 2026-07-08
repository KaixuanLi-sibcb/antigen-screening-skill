from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.coverage_diagnostics import build_coverage_diagnostics, run_coverage_diagnostics
from antigen_screening.io import write_tsv


class CoverageDiagnosticsTest(unittest.TestCase):
    def test_missing_hpa_is_adapter_not_run_not_low_risk(self) -> None:
        rows = [
            {
                "candidate_id": "C1",
                "gene_symbol": "PDCD1",
                "species": "human",
                "modality": "car_t",
                "uniprot_accession": "Q15116",
                "ensembl_gene_id": "ENSG00000188389",
                "ecd_region": "25..167",
                "constructability_gate": "pass",
                "mouse_model_transferability_gate": "pass",
            }
        ]
        coverage, _, _, _ = build_coverage_diagnostics(rows)
        self.assertEqual(coverage[0]["hpa_status"], "adapter_not_run")
        self.assertNotEqual(coverage[0]["normal_tissue_status"], "low")
        self.assertIn(coverage[0]["missing_reason_primary"], {"id_mapping_missing", "adapter_not_run"})

    def test_no_ensembl_id_gets_id_mapping_missing(self) -> None:
        rows = [{"candidate_id": "C1", "gene_symbol": "CD19", "species": "human", "modality": "car_t"}]
        coverage, _, _, _ = build_coverage_diagnostics(rows)
        self.assertEqual(coverage[0]["ensembl_status"], "id_mapping_missing")
        self.assertIn("id_mapping_missing", coverage[0]["missing_reason_secondary"] + ";" + coverage[0]["missing_reason_primary"])

    def test_ambiguous_alias_gets_id_mapping_ambiguous(self) -> None:
        rows = [{"candidate_id": "C1", "gene_symbol": "ABC", "species": "human", "modality": "antibody"}]
        coverage, id_rows, _, _ = build_coverage_diagnostics(rows, alias_map={"ABC": ["ABCA1", "ABCB1"]})
        self.assertEqual(id_rows[0]["mapping_status"], "ambiguous_alias")
        self.assertEqual(coverage[0]["missing_reason_primary"], "id_mapping_ambiguous")

    def test_local_tabular_evidence_does_not_become_live(self) -> None:
        rows = [
            {
                "candidate_id": "C1",
                "gene_symbol": "ALB",
                "species": "human",
                "modality": "soluble_ecd_screen",
                "uniprot_accession": "P02768",
                "known_evidence": "2",
                "mouse_model_transferability_gate": "pass",
            }
        ]
        coverage, _, _, _ = build_coverage_diagnostics(rows)
        self.assertEqual(coverage[0]["uniprot_status"], "confirmed_local_xlsx")
        self.assertNotEqual(coverage[0]["live_ecd_status"], "confirmed_live")
        self.assertEqual(coverage[0]["opentargets_status"], "adapter_not_implemented")

    def test_cli_outputs_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "screening.tsv"
            write_tsv(
                input_path,
                [{"candidate_id": "C1", "gene_symbol": "MKI67", "species": "human", "modality": "antibody"}],
                ["candidate_id", "gene_symbol", "species", "modality"],
            )
            summary = run_coverage_diagnostics(screening_table=input_path, outdir=root / "coverage")
            self.assertEqual(summary["status"], "pass")
            for name in [
                "coverage_diagnostics.tsv",
                "id_mapping_rescue.tsv",
                "missingness_reason_summary.json",
                "adapter_readiness_matrix.tsv",
                "coverage_report.md",
            ]:
                self.assertTrue((root / "coverage" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
