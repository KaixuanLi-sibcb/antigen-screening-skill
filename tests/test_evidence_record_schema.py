from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.evidence import fixture_evidence_record
from validate_evidence_records import validate_record


SCHEMA = json.loads((ROOT / "schemas" / "evidence_record.schema.json").read_text(encoding="utf-8"))


class EvidenceRecordSchemaTest(unittest.TestCase):
    def test_valid_evidence_record_v2_passes(self) -> None:
        record = fixture_evidence_record(
            candidate_id="CAND0001",
            gene_symbol="CD19",
            uniprot_accession="P15391",
            evidence_type="topology",
            evidence_value="surface_single_pass",
            fixture_source="tests/fixtures/uniprot_CD19_human.json",
        )
        self.assertEqual(validate_record(record, SCHEMA, 1), [])

    def test_missing_required_field_fails(self) -> None:
        record = fixture_evidence_record(
            candidate_id="CAND0001",
            gene_symbol="CD19",
            evidence_type="topology",
            evidence_value="surface_single_pass",
        )
        record.pop("source_name")
        self.assertTrue(any("missing required fields" in error for error in validate_record(record, SCHEMA, 1)))

    def test_invalid_evidence_status_fails(self) -> None:
        record = fixture_evidence_record(
            candidate_id="CAND0001",
            gene_symbol="CD19",
            evidence_type="topology",
            evidence_value="surface_single_pass",
        )
        record["evidence_status"] = "negative"
        self.assertTrue(any("invalid evidence_status" in error for error in validate_record(record, SCHEMA, 1)))


if __name__ == "__main__":
    unittest.main()
