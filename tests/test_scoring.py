from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.io import normalize_candidate_rows, read_tsv
from antigen_screening.scoring import evaluate_candidate
from antigen_screening.uniprot_parser import fixture_index


FIXTURES = ROOT / "tests" / "fixtures"


class ScoringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = {row["gene_symbol"]: row for row in normalize_candidate_rows(read_tsv(FIXTURES / "candidate_input.tsv"))}
        cls.index = fixture_index(FIXTURES)

    def _score(self, gene: str) -> dict[str, str]:
        row, _, _ = evaluate_candidate(self.rows[gene], self.index[gene], 0.70)
        return row

    def test_cd19_car_surface_pass(self) -> None:
        row = self._score("CD19")
        self.assertEqual(row["accessibility_gate"], "pass")
        self.assertEqual(row["modality_gate"], "pass")

    def test_alb_car_flagged_not_surface(self) -> None:
        row = self._score("ALB")
        self.assertEqual(row["antigen_accessibility"], "secreted")
        self.assertEqual(row["modality_gate"], "fail")
        self.assertIn("secreted_not_cell_surface", row["risk_flags"])
        self.assertEqual(row["priority_call"], "control_or_not_applicable")

    def test_mki67_surface_fail(self) -> None:
        row = self._score("MKI67")
        self.assertEqual(row["accessibility_gate"], "fail")
        self.assertEqual(row["priority_call"], "no_go")


if __name__ == "__main__":
    unittest.main()
