from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.report_priority import rank_candidates, run_report_priority
from antigen_screening.io import write_tsv, CANDIDATE_OUTPUT_COLUMNS, CONSTRUCT_COLUMNS


def candidate(gene: str, identity: str, mouse_gate: str = "fail", normal: str = "unknown") -> dict[str, str]:
    return {
        "candidate_id": gene,
        "input_name": gene,
        "species": "human",
        "gene_symbol": gene,
        "modality": "soluble_ecd_screen",
        "disease_context": "fixture",
        "user_evidence": "",
        "uniprot_accession": f"P{gene}",
        "protein_name": f"{gene} protein",
        "antigen_accessibility": "cell_surface_single_pass",
        "accessibility_gate": "pass",
        "accessibility_evidence_state": "confirmed_local_xlsx",
        "topology_evidence": "",
        "ecd_region": "20..220",
        "ecd_length": "200",
        "ecd_evidence_state": "confirmed_local_xlsx",
        "ecd_boundary_confidence": "medium",
        "ecd_notes": "",
        "isoform_risk": "missing_live_isoform_review",
        "disease_relevance_gate": "uncertain",
        "disease_evidence_state": "missing",
        "normal_tissue_risk": normal,
        "normal_tissue_risk_evidence_state": "missing",
        "mouse_model_transferability_gate": mouse_gate,
        "human_mouse_ecd_identity": identity,
        "ecd_identity_threshold": "0.70",
        "orthology_evidence_state": "confirmed_local_xlsx",
        "constructability_gate": "pass",
        "constructability_class": "soluble_ecd_construct",
        "modality_fit": "soluble_ecd_screen_triage",
        "modality_gate": "pass",
        "modality_evidence_state": "inferred_from_local_xlsx",
        "known_evidence": "",
        "risk_flags": "mouse_ecd_identity_below_threshold" if mouse_gate == "fail" else "",
        "tie_break_score": "0",
        "priority_call": "no_go" if mouse_gate == "fail" else "go",
        "decision_rationale": "fixture",
        "missing_evidence": "",
    }


class ReportPriorityTest(unittest.TestCase):
    def test_low_mouse_identity_is_positive_for_antibody_screening(self) -> None:
        rows = [
            candidate("HIGHID", "0.95", "pass"),
            candidate("LOWID", "0.45", "fail"),
        ]
        ranked = rank_candidates(rows, identity_preference="low_for_antibody_screening")
        self.assertEqual(ranked[0]["gene_symbol"], "LOWID")
        self.assertEqual(ranked[0]["rank_bucket"], "A")
        self.assertEqual(ranked[0]["original_mouse_model_transferability_gate"], "fail")
        self.assertIn("high_divergence_priority", ranked[0]["passed_reasons"])

    def test_high_normal_tissue_risk_still_deprioritizes(self) -> None:
        ranked = rank_candidates(
            [candidate("LOWID", "0.45", "fail")],
            normal_tissue_rows=[{"candidate_id": "LOWID", "gene_symbol": "LOWID", "normal_tissue_risk": "high", "high_risk_tissue_flags": "liver"}],
        )
        self.assertEqual(ranked[0]["rank_bucket"], "D")
        self.assertIn("high_normal_tissue_risk", ranked[0]["caution_or_fail_reasons"])

    def test_accessibility_fail_still_deprioritizes(self) -> None:
        row = candidate("NUCLEAR", "0.45", "fail")
        row["accessibility_gate"] = "fail"
        row["antigen_accessibility"] = "intracellular_or_unknown"
        ranked = rank_candidates([row])
        self.assertEqual(ranked[0]["rank_bucket"], "D")

    def test_export_writes_required_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            screening = root / "screening.tsv"
            construct = root / "construct.tsv"
            write_tsv(screening, [candidate("LOWID", "0.45", "fail")], CANDIDATE_OUTPUT_COLUMNS)
            write_tsv(
                construct,
                [
                    {
                        "gene_symbol": "LOWID",
                        "modality": "soluble_ecd_screen",
                        "accessibility_gate": "pass",
                        "constructability_gate": "pass",
                        "ecd_region": "20..220",
                        "ecd_length": "200",
                        "construct_recommendation": "soluble_ecd_construct",
                    }
                ],
                CONSTRUCT_COLUMNS,
            )
            summary = run_report_priority(screening_table=screening, construct_plan=construct, outdir=root / "ranked")
            self.assertEqual(summary["status"], "pass")
            self.assertTrue((root / "ranked" / "report_priority_table.tsv").exists())
            self.assertTrue((root / "ranked" / "report_priority_workbook.xlsx").exists())


if __name__ == "__main__":
    unittest.main()
