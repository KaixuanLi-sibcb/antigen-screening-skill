from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.evidence import fixture_evidence_record
from validate_evidence_records import validate_jsonl


SCHEMA = ROOT / "schemas" / "evidence_record.schema.json"


class EvidenceProvenanceValidatorTest(unittest.TestCase):
    def test_validator_accepts_fixture_smoke_style_jsonl(self) -> None:
        record = fixture_evidence_record(
            candidate_id="CAND0001",
            gene_symbol="PDCD1",
            uniprot_accession="Q15116",
            evidence_type="topology",
            evidence_value="surface_single_pass",
            fixture_source="tests/fixtures/uniprot_PDCD1_human.json",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence_records.jsonl"
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            summary = validate_jsonl(path, SCHEMA)
        self.assertEqual(summary["status"], "pass")

    def test_validator_fails_on_broken_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.jsonl"
            path.write_text("{not-json}\n", encoding="utf-8")
            summary = validate_jsonl(path, SCHEMA)
        self.assertEqual(summary["status"], "fail")
        self.assertTrue(any("invalid JSON" in error for error in summary["errors"]))


if __name__ == "__main__":
    unittest.main()
