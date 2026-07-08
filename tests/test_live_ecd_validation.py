from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.live_ecd import pairwise_identity, validate_ecd_identity
from antigen_screening.live_ensembl import load_ensembl_source, parse_orthologies
from antigen_screening.live_uniprot import load_uniprot_source, normalize_live_uniprot
from validate_evidence_records import validate_jsonl


UNIPROT = ROOT / "tests" / "fixtures" / "live_uniprot"
ENSEMBL = ROOT / "tests" / "fixtures" / "live_ensembl"
SCHEMA = ROOT / "schemas" / "evidence_record.schema.json"


class LiveEcdValidationTest(unittest.TestCase):
    def test_pairwise_identity_handles_equal_and_unequal_sequences(self) -> None:
        self.assertEqual(pairwise_identity("AAAA", "AAAA"), 1.0)
        self.assertAlmostEqual(pairwise_identity("AAAA", "AAAT") or 0, 0.75)
        self.assertAlmostEqual(pairwise_identity("AAAA", "AAA") or 0, 0.75)

    def test_fixture_ecd_identity_matches_local_value_without_conflict(self) -> None:
        _, uniprot_raw, _ = load_uniprot_source(offline_fixture=UNIPROT / "Q15116.json", no_network=True)
        human = normalize_live_uniprot(uniprot_raw or {}, str(UNIPROT / "Q15116.json"))
        _, ensembl_raw, _ = load_ensembl_source(gene_symbol="PDCD1", offline_fixture=ENSEMBL / "PDCD1_human_mouse.json")
        orthologs = parse_orthologies(ensembl_raw or {})
        summary, records, conflicts = validate_ecd_identity(
            human_record=human,
            ortholog=orthologs[0],
            candidate_id="Q15116",
            gene_symbol="PDCD1",
            local_ecd_identity="1.0",
            source_kind="fixture",
        )
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(conflicts, [])
        self.assertIn("live_computed_ecd_identity", {record["evidence_type"] for record in records})

    def test_local_vs_computed_identity_conflict_is_explicit(self) -> None:
        _, uniprot_raw, _ = load_uniprot_source(offline_fixture=UNIPROT / "Q15116.json", no_network=True)
        human = normalize_live_uniprot(uniprot_raw or {}, str(UNIPROT / "Q15116.json"))
        _, ensembl_raw, _ = load_ensembl_source(gene_symbol="PDCD1", offline_fixture=ENSEMBL / "PDCD1_human_mouse.json")
        orthologs = parse_orthologies(ensembl_raw or {})
        summary, records, conflicts = validate_ecd_identity(
            human_record=human,
            ortholog=orthologs[0],
            candidate_id="Q15116",
            gene_symbol="PDCD1",
            local_ecd_identity="0.5",
            tolerance=0.05,
            source_kind="fixture",
        )
        self.assertEqual(summary["status"], "conflict")
        self.assertEqual(len(conflicts), 1)
        self.assertIn("conflict", {record["evidence_status"] for record in records})

    def test_missing_topology_yields_missing_evidence_not_negative(self) -> None:
        _, uniprot_raw, _ = load_uniprot_source(offline_fixture=UNIPROT / "TOPOLOGY_MISSING.json", no_network=True)
        human = normalize_live_uniprot(uniprot_raw or {}, str(UNIPROT / "TOPOLOGY_MISSING.json"))
        summary, records, conflicts = validate_ecd_identity(
            human_record=human,
            ortholog=None,
            candidate_id="NOTOP",
            gene_symbol="NOTOP",
            local_ecd_identity="",
            source_kind="fixture",
        )
        self.assertEqual(summary["status"], "missing")
        self.assertEqual(conflicts, [])
        self.assertEqual(records[0]["evidence_status"], "missing")
        self.assertNotIn("negative", records[0]["failure_mode"].lower())

    def test_cli_fixture_output_validates_and_writes_conflict_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp) / "live_ecd"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_live_ecd_validation.py"),
                    "--gene-symbol",
                    "PDCD1",
                    "--accession",
                    "Q15116",
                    "--outdir",
                    str(outdir),
                    "--human-uniprot-fixture",
                    str(UNIPROT / "Q15116.json"),
                    "--ensembl-fixture",
                    str(ENSEMBL / "PDCD1_human_mouse.json"),
                    "--local-ecd-identity",
                    "0.5",
                    "--no-network",
                    "--pretty",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((outdir / "live_ecd_conflicts.tsv").exists())
            summary = validate_jsonl(outdir / "live_ecd_evidence_records.jsonl", SCHEMA)
            self.assertEqual(summary["status"], "pass")


if __name__ == "__main__":
    unittest.main()
