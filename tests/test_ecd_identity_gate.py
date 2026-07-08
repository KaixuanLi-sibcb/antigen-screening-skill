from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.report_priority import rank_candidates


class EcdIdentityGateTest(unittest.TestCase):
    def test_low_identity_ranks_higher_for_antibody_screening_mode(self) -> None:
        rows = [
            {
                "candidate_id": "C1",
                "gene_symbol": "LOWID",
                "antigen_accessibility": "cell_surface_single_pass",
                "accessibility_gate": "pass",
                "constructability_gate": "pass",
                "human_mouse_ecd_identity": "0.30",
                "mouse_model_transferability_gate": "fail",
                "normal_tissue_risk": "unknown",
            },
            {
                "candidate_id": "C2",
                "gene_symbol": "HIGHID",
                "antigen_accessibility": "cell_surface_single_pass",
                "accessibility_gate": "pass",
                "constructability_gate": "pass",
                "human_mouse_ecd_identity": "0.95",
                "mouse_model_transferability_gate": "pass",
                "normal_tissue_risk": "unknown",
            },
        ]
        ranked = rank_candidates(rows, identity_preference="low_for_antibody_screening")
        self.assertEqual(ranked[0]["gene_symbol"], "LOWID")
        self.assertEqual(ranked[0]["human_mouse_divergence_class"], "high_divergence_priority")
        self.assertEqual(ranked[0]["original_mouse_model_transferability_gate"], "fail")


if __name__ == "__main__":
    unittest.main()
