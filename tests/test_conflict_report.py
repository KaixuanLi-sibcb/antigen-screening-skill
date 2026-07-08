from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.evidence import fixture_evidence_record, local_xlsx_evidence_record
from antigen_screening.evidence_conflict import detect_conflicts, write_conflict_report


class ConflictReportTest(unittest.TestCase):
    def test_value_conflict_reported_for_same_candidate_and_evidence_type(self) -> None:
        records = [
            fixture_evidence_record(
                candidate_id="C1",
                gene_symbol="CD19",
                evidence_type="topology",
                evidence_value="surface_single_pass",
                normalized_value="pass",
            ),
            local_xlsx_evidence_record(
                candidate_id="C1",
                gene_symbol="CD19",
                evidence_type="topology",
                evidence_value="intracellular_or_unknown",
                normalized_value="uncertain",
                source_name="local_tabular_topology",
            ),
        ]
        conflicts = detect_conflicts(records)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["conflict_status"], "value_conflict")
        with tempfile.TemporaryDirectory() as tmp:
            summary = write_conflict_report(records, Path(tmp))
            report = (Path(tmp) / "evidence_conflicts.tsv").read_text(encoding="utf-8")
            summary_file = json.loads((Path(tmp) / "evidence_conflict_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["conflict_count"], 1)
        self.assertEqual(summary_file["conflict_count"], 1)
        self.assertIn("value_conflict", report)


if __name__ == "__main__":
    unittest.main()
