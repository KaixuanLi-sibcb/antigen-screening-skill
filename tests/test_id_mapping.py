from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.id_mapping import rescue_identifier


class IdMappingTest(unittest.TestCase):
    def test_exact_symbol_mapping(self) -> None:
        row = rescue_identifier({"candidate_id": "C1", "gene_symbol": "PDCD1"})
        self.assertEqual(row["mapping_status"], "resolved_exact")
        self.assertEqual(row["resolved_symbol"], "PDCD1")

    def test_alias_mapping(self) -> None:
        row = rescue_identifier({"candidate_id": "C2", "gene_symbol": "PD1"}, alias_map={"PD1": "PDCD1"})
        self.assertEqual(row["mapping_status"], "resolved_alias")
        self.assertEqual(row["resolved_symbol"], "PDCD1")
        self.assertEqual(row["recommended_action"], "not_applicable_no_action")

    def test_uniprot_first_mapping(self) -> None:
        row = rescue_identifier(
            {"candidate_id": "C3", "uniprot_accession": "P15391"},
            uniprot_map={"P15391": {"gene_symbol": "CD19", "ensembl_gene_id": "ENSG00000177455"}},
        )
        self.assertEqual(row["mapping_status"], "resolved_uniprot")
        self.assertEqual(row["resolved_symbol"], "CD19")
        self.assertEqual(row["resolved_ensembl"], "ENSG00000177455")

    def test_ensembl_mapping(self) -> None:
        row = rescue_identifier(
            {"candidate_id": "C4", "ensembl_gene_id": "ENSG00000177455"},
            ensembl_map={"ENSG00000177455": {"gene_symbol": "CD19", "uniprot_accession": "P15391"}},
        )
        self.assertEqual(row["mapping_status"], "resolved_ensembl")
        self.assertEqual(row["resolved_symbol"], "CD19")
        self.assertEqual(row["resolved_uniprot"], "P15391")

    def test_ambiguous_alias_mapping(self) -> None:
        row = rescue_identifier({"candidate_id": "C5", "gene_symbol": "ABC"}, alias_map={"ABC": ["ABCA1", "ABCB1"]})
        self.assertEqual(row["mapping_status"], "ambiguous_alias")
        self.assertEqual(row["recommended_action"], "manual_review_alias")
        self.assertIn("ABCA1", row["ambiguous_candidates"])

    def test_conflicting_mapping(self) -> None:
        row = rescue_identifier(
            {"candidate_id": "C6", "gene_symbol": "PD1", "uniprot_accession": "P15391"},
            alias_map={"PD1": "PDCD1"},
            uniprot_map={"P15391": {"gene_symbol": "CD19"}},
        )
        self.assertEqual(row["mapping_status"], "conflict")
        self.assertEqual(row["conflict_status"], "source_conflict")

    def test_missing_identifier(self) -> None:
        row = rescue_identifier({"candidate_id": "C7"})
        self.assertEqual(row["mapping_status"], "missing_identifier")
        self.assertEqual(row["recommended_action"], "add_hgnc_mapping")


if __name__ == "__main__":
    unittest.main()
