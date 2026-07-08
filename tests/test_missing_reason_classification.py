from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.coverage_diagnostics import build_coverage_diagnostics


class MissingReasonClassificationTest(unittest.TestCase):
    def test_blank_values_do_not_become_negative(self) -> None:
        coverage, _, _, _ = build_coverage_diagnostics([{"candidate_id": "C1", "gene_symbol": "", "species": "human", "modality": "adc"}])
        self.assertEqual(coverage[0]["evidence_status_overall"], "missing")
        self.assertNotIn("negative", coverage[0]["notes"])

    def test_missing_normal_tissue_is_not_low_risk(self) -> None:
        coverage, _, _, _ = build_coverage_diagnostics([{"candidate_id": "C1", "gene_symbol": "CD19", "species": "human", "modality": "car_t"}])
        self.assertNotEqual(coverage[0]["normal_tissue_status"], "low")
        self.assertIn(coverage[0]["hpa_status"], {"adapter_not_run", "source_record_missing"})

    def test_open_targets_pending_is_not_no_drug_evidence(self) -> None:
        coverage, _, _, _ = build_coverage_diagnostics([{"candidate_id": "C1", "gene_symbol": "EGFR", "species": "human", "modality": "antibody"}])
        self.assertEqual(coverage[0]["opentargets_status"], "adapter_not_implemented")
        self.assertNotEqual(coverage[0]["drug_evidence_status"], "no_drug_evidence")


if __name__ == "__main__":
    unittest.main()
