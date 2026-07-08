from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.ecd import extract_ecd
from antigen_screening.topology import classify_accessibility
from antigen_screening.uniprot_parser import load_uniprot_json


FIXTURES = ROOT / "tests" / "fixtures"


class EcdTest(unittest.TestCase):
    def _ecd(self, name: str) -> dict[str, str]:
        record = load_uniprot_json(FIXTURES / name)
        return extract_ecd(record, classify_accessibility(record))

    def test_cd19_explicit_ecd(self) -> None:
        ecd = self._ecd("uniprot_CD19_human.json")
        self.assertEqual(ecd["ecd_region"], "20-291")
        self.assertEqual(ecd["ecd_evidence_state"], "confirmed")
        self.assertEqual(ecd["ecd_boundary_confidence"], "high")

    def test_alb_secreted_chain(self) -> None:
        ecd = self._ecd("uniprot_ALB_human.json")
        self.assertEqual(ecd["ecd_region"], "25-609")
        self.assertIn("secreted_only", ecd["ecd_flags"])

    def test_mki67_no_ecd(self) -> None:
        ecd = self._ecd("uniprot_MKI67_human.json")
        self.assertEqual(ecd["ecd_region"], "not_applicable")
        self.assertEqual(ecd["ecd_evidence_state"], "not_applicable")


if __name__ == "__main__":
    unittest.main()
