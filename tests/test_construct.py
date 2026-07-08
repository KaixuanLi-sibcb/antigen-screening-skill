from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.construct import construct_plan_for
from antigen_screening.io import normalize_candidate_rows, read_tsv
from antigen_screening.scoring import evaluate_candidate
from antigen_screening.uniprot_parser import fixture_index


FIXTURES = ROOT / "tests" / "fixtures"


class ConstructTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        input_rows = {row["gene_symbol"]: row for row in normalize_candidate_rows(read_tsv(FIXTURES / "candidate_input.tsv"))}
        index = fixture_index(FIXTURES)
        cls.scored = {gene: evaluate_candidate(row, index[gene], 0.70)[0] for gene, row in input_rows.items()}

    def test_cd19_construct(self) -> None:
        plan = construct_plan_for(self.scored["CD19"])
        self.assertEqual(plan["construct_recommendation"], "soluble_ecd_construct")
        self.assertEqual(plan["remove_tm"], "yes")
        self.assertEqual(plan["remove_cytoplasmic_tail"], "yes")

    def test_alb_control_only(self) -> None:
        plan = construct_plan_for(self.scored["ALB"])
        self.assertEqual(plan["construct_recommendation"], "soluble_protein_control_only")
        self.assertIn("not a cell-surface target", plan["stop_condition"])

    def test_mki67_no_construct(self) -> None:
        plan = construct_plan_for(self.scored["MKI67"])
        self.assertEqual(plan["construct_recommendation"], "no_construct")


if __name__ == "__main__":
    unittest.main()
