from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.evidence import local_xlsx_evidence_record, make_evidence_record, missing_evidence_record
from validate_evidence_records import validate_record


SCHEMA = json.loads((ROOT / "schemas" / "evidence_record.schema.json").read_text(encoding="utf-8"))


class MissingIsNotNegativeTest(unittest.TestCase):
    def test_missing_record_has_no_evidence_value(self) -> None:
        record = missing_evidence_record(candidate_id="C1", gene_symbol="MKI67", evidence_type="normal_tissue_live_data")
        self.assertEqual(record["evidence_status"], "missing")
        self.assertEqual(record["evidence_value"], "")
        self.assertEqual(record["normalized_value"], "")
        self.assertNotIn("negative", json.dumps(record).lower())
        self.assertEqual(validate_record(record, SCHEMA, 1), [])

    def test_blank_local_xlsx_value_becomes_missing_not_false(self) -> None:
        record = local_xlsx_evidence_record(
            candidate_id="C1",
            gene_symbol="MKI67",
            evidence_type="local_tabular_ecd_identity",
            evidence_value="",
            source_name="local_tabular_ecd_identity",
        )
        self.assertEqual(record["evidence_status"], "missing")
        self.assertEqual(record["evidence_value"], "")
        self.assertNotEqual(record["normalized_value"].lower(), "false")

    def test_missing_status_clears_supplied_false_like_value(self) -> None:
        record = make_evidence_record(
            candidate_id="C1",
            gene_symbol="MKI67",
            evidence_type="normal_tissue_live_data",
            evidence_value="false",
            evidence_status="missing",
            source_name="future_hpa_gtex_adapter",
        )
        self.assertEqual(record["evidence_value"], "")
        self.assertEqual(record["normalized_value"], "")


if __name__ == "__main__":
    unittest.main()
