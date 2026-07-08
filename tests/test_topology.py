from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.topology import classify_accessibility
from antigen_screening.uniprot_parser import load_uniprot_json


FIXTURES = ROOT / "tests" / "fixtures"


class TopologyTest(unittest.TestCase):
    def test_pdcd1_surface(self) -> None:
        record = load_uniprot_json(FIXTURES / "uniprot_PDCD1_human.json")
        result = classify_accessibility(record)
        self.assertEqual(result["accessibility_gate"], "pass")
        self.assertEqual(result["antigen_accessibility"], "surface_single_pass")

    def test_alb_secreted(self) -> None:
        record = load_uniprot_json(FIXTURES / "uniprot_ALB_human.json")
        result = classify_accessibility(record)
        self.assertEqual(result["accessibility_gate"], "pass")
        self.assertEqual(result["antigen_accessibility"], "secreted")

    def test_mki67_intracellular_fail(self) -> None:
        record = load_uniprot_json(FIXTURES / "uniprot_MKI67_human.json")
        result = classify_accessibility(record)
        self.assertEqual(result["accessibility_gate"], "fail")
        self.assertEqual(result["antigen_accessibility"], "intracellular_or_nuclear")


if __name__ == "__main__":
    unittest.main()
