from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.live_ensembl import ensembl_evidence_records, load_ensembl_source, parse_orthologies
from validate_evidence_records import validate_jsonl


FIXTURES = ROOT / "tests" / "fixtures" / "live_ensembl"
SCHEMA = ROOT / "schemas" / "evidence_record.schema.json"


class LiveEnsemblAdapterTest(unittest.TestCase):
    def test_fixture_mode_parses_one_to_one_ortholog_and_evidence_v2(self) -> None:
        kind, raw, metadata = load_ensembl_source(gene_symbol="PDCD1", offline_fixture=FIXTURES / "PDCD1_human_mouse.json")
        self.assertEqual(kind, "fixture")
        orthologs = parse_orthologies(raw or {})
        self.assertEqual(len(orthologs), 1)
        self.assertEqual(orthologs[0]["target_gene_symbol"], "Pdcd1")
        records, parsed = ensembl_evidence_records(
            raw=raw,
            kind=kind,
            metadata=metadata,
            candidate_id="PDCD1",
            gene_symbol="PDCD1",
            species="human",
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual({record["evidence_status"] for record in records}, {"confirmed_fixture"})

    def test_fixture_controls_have_orthology_without_surface_claims(self) -> None:
        for fixture, gene in [
            ("CD19_human_mouse.json", "CD19"),
            ("ALB_human_mouse.json", "ALB"),
            ("MKI67_human_mouse.json", "MKI67"),
        ]:
            with self.subTest(gene=gene):
                kind, raw, metadata = load_ensembl_source(gene_symbol=gene, offline_fixture=FIXTURES / fixture)
                records, orthologs = ensembl_evidence_records(
                    raw=raw,
                    kind=kind,
                    metadata=metadata,
                    candidate_id=gene,
                    gene_symbol=gene,
                    species="human",
                )
                self.assertEqual(len(orthologs), 1)
                self.assertTrue(all(record["evidence_type"].startswith("ensembl_ortholog") for record in records))
                self.assertNotIn("surface", json.dumps(records).lower())

    def test_no_network_without_fixture_returns_missing_not_negative(self) -> None:
        kind, raw, metadata = load_ensembl_source(gene_symbol="PDCD1", no_network=True)
        records, orthologs = ensembl_evidence_records(
            raw=raw,
            kind=kind,
            metadata=metadata,
            candidate_id="PDCD1",
            gene_symbol="PDCD1",
            species="human",
        )
        self.assertEqual(kind, "missing")
        self.assertEqual(orthologs, [])
        self.assertEqual(records[0]["evidence_status"], "missing")
        self.assertNotIn("negative", json.dumps(records[0]).lower())

    def test_no_ortholog_fixture_returns_missing(self) -> None:
        kind, raw, metadata = load_ensembl_source(gene_symbol="NOPE", offline_fixture=FIXTURES / "NO_ORTHOLOG.json")
        records, orthologs = ensembl_evidence_records(
            raw=raw,
            kind=kind,
            metadata=metadata,
            candidate_id="NOPE",
            gene_symbol="NOPE",
            species="human",
        )
        self.assertEqual(orthologs, [])
        self.assertEqual(records[0]["evidence_status"], "missing")
        self.assertEqual(records[0]["failure_mode"], "no_mouse_ortholog_returned")

    def test_ambiguous_orthologs_emit_conflict_record(self) -> None:
        kind, raw, metadata = load_ensembl_source(gene_symbol="TEST", offline_fixture=FIXTURES / "AMBIGUOUS.json")
        records, orthologs = ensembl_evidence_records(
            raw=raw,
            kind=kind,
            metadata=metadata,
            candidate_id="TEST",
            gene_symbol="TEST",
            species="human",
        )
        self.assertEqual(len(orthologs), 2)
        conflicts = [record for record in records if record["evidence_status"] == "conflict"]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["conflict_status"], "source_conflict")

    def test_cli_fixture_output_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp) / "ensembl"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "fetch_live_orthology.py"),
                    "--gene-symbol",
                    "PDCD1",
                    "--outdir",
                    str(outdir),
                    "--offline-fixture",
                    str(FIXTURES / "PDCD1_human_mouse.json"),
                    "--no-network",
                    "--pretty",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = validate_jsonl(outdir / "ensembl_evidence_records.jsonl", SCHEMA)
            self.assertEqual(summary["status"], "pass")


if __name__ == "__main__":
    unittest.main()
