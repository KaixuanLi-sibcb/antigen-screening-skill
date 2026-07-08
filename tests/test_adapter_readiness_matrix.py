from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.coverage_diagnostics import ADAPTER_STATUSES, adapter_readiness_matrix


class AdapterReadinessMatrixTest(unittest.TestCase):
    def test_expected_adapters_are_listed(self) -> None:
        names = {row["adapter_name"] for row in adapter_readiness_matrix()}
        expected = {
            "uniprot",
            "ensembl_orthology",
            "live_ecd_validation",
            "hpa",
            "gtex",
            "opentargets",
            "chembl",
            "clinicaltrials",
            "local_tabular_evidence",
            "construct_planner",
            "screening_strategy",
            "validation_ladder",
        }
        self.assertEqual(expected, names)

    def test_statuses_use_controlled_vocabulary(self) -> None:
        for row in adapter_readiness_matrix():
            self.assertIn(row["current_status"], ADAPTER_STATUSES)

    def test_ci_and_offline_availability_are_explicit(self) -> None:
        for row in adapter_readiness_matrix():
            self.assertTrue(row["offline_fixture_available"])
            self.assertTrue(row["ci_enabled"])


if __name__ == "__main__":
    unittest.main()
