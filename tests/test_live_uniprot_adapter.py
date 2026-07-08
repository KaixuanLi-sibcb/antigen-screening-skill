from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.live_uniprot import load_uniprot_source, normalize_live_uniprot, uniprot_evidence_records
from validate_evidence_records import validate_jsonl


FIXTURES = ROOT / "tests" / "fixtures" / "live_uniprot"
SCHEMA = ROOT / "schemas" / "evidence_record.schema.json"


class LiveUniProtAdapterTest(unittest.TestCase):
    def test_fixture_mode_parses_uniprot_record_and_evidence_v2(self) -> None:
        kind, raw, metadata = load_uniprot_source(offline_fixture=FIXTURES / "Q15116.json", no_network=True)
        self.assertEqual(kind, "fixture")
        normalized = normalize_live_uniprot(raw or {}, str(FIXTURES / "Q15116.json"))
        self.assertEqual(normalized["accession"], "Q15116")
        self.assertEqual(normalized["gene_symbol"], "PDCD1")
        self.assertEqual(normalized["review_status"], "reviewed")
        self.assertTrue(normalized["sequence"])
        records = uniprot_evidence_records(
            normalized=normalized,
            raw=raw,
            kind=kind,
            metadata=metadata,
            candidate_id="Q15116",
            gene_symbol="PDCD1",
            species="human",
            query={"accession": "Q15116"},
        )
        statuses = {record["evidence_status"] for record in records}
        self.assertEqual(statuses, {"confirmed_fixture"})

    def test_no_network_without_fixture_returns_missing_record(self) -> None:
        kind, raw, metadata = load_uniprot_source(accession="Q15116", no_network=True)
        records = uniprot_evidence_records(
            normalized=None,
            raw=raw,
            kind=kind,
            metadata=metadata,
            candidate_id="Q15116",
            gene_symbol="PDCD1",
            species="human",
            query={"accession": "Q15116"},
        )
        self.assertEqual(kind, "missing")
        self.assertEqual(records[0]["evidence_status"], "missing")
        self.assertNotIn("negative", json.dumps(records[0]).lower())

    def test_malformed_fixture_returns_error_record(self) -> None:
        kind, raw, metadata = load_uniprot_source(offline_fixture=FIXTURES / "MALFORMED.json", no_network=True)
        records = uniprot_evidence_records(
            normalized=None,
            raw=raw,
            kind=kind,
            metadata=metadata,
            candidate_id="BAD",
            gene_symbol="BAD",
            species="human",
            query={"fixture": "MALFORMED.json"},
        )
        self.assertEqual(kind, "error")
        self.assertEqual(records[0]["evidence_status"], "error")
        self.assertIn("JSONDecodeError", records[0]["failure_mode"])

    def test_missing_topology_is_missing_not_negative(self) -> None:
        kind, raw, metadata = load_uniprot_source(offline_fixture=FIXTURES / "TOPOLOGY_MISSING.json", no_network=True)
        normalized = normalize_live_uniprot(raw or {}, str(FIXTURES / "TOPOLOGY_MISSING.json"))
        records = uniprot_evidence_records(
            normalized=normalized,
            raw=raw,
            kind=kind,
            metadata=metadata,
            candidate_id="NOTOP",
            gene_symbol="NOTOP",
            species="human",
            query={"accession": "P99999"},
        )
        topology = [record for record in records if record["evidence_type"] == "uniprot_topology_features"][0]
        self.assertEqual(topology["evidence_status"], "missing")
        self.assertEqual(topology["evidence_value"], "")
        self.assertNotIn("negative", json.dumps(topology).lower())

    def test_cli_fixture_output_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp) / "uniprot"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "fetch_live_uniprot.py"),
                    "--accession",
                    "Q15116",
                    "--outdir",
                    str(outdir),
                    "--offline-fixture",
                    str(FIXTURES / "Q15116.json"),
                    "--no-network",
                    "--pretty",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = validate_jsonl(outdir / "uniprot_evidence_records.jsonl", SCHEMA)
            self.assertEqual(summary["status"], "pass")


if __name__ == "__main__":
    unittest.main()
