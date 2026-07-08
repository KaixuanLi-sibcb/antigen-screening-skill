from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.io import read_tsv, write_tsv
from antigen_screening.screening_strategy import SCREENING_STRATEGY_COLUMNS
from antigen_screening.validation_ladder import ladder_for_row


def row(**updates: str) -> dict[str, str]:
    base = {column: "" for column in SCREENING_STRATEGY_COLUMNS}
    base.update({"candidate_id": "C1", "gene_symbol": "TEST", "primary_strategy": "soluble_ecd"})
    base.update(updates)
    return base


class ValidationLadderTest(unittest.TestCase):
    def test_ladder_contains_required_validation_layers(self) -> None:
        stages = {item["validation_stage"] for item in ladder_for_row(row())}
        required = {
            "orthogonal_validation",
            "genetic_validation",
            "independent_reagent_validation",
            "tagged_protein_validation",
            "flow_cell_binding_validation",
            "knockout_knockdown_loss_of_binding",
            "overexpression_gain_of_binding",
            "immunocapture_ms_optional",
        }
        self.assertTrue(required.issubset(stages))

    def test_cross_species_added_when_mouse_model_needed(self) -> None:
        stages = {item["validation_stage"] for item in ladder_for_row(row(notes="mouse model needed"))}
        self.assertIn("cross_species_binding", stages)

    def test_not_recommended_strategy_preserves_stop_note(self) -> None:
        rows = ladder_for_row(row(primary_strategy="not_recommended"))
        self.assertTrue(any("not recommended" in item["notes"] for item in rows))

    def test_cli_writes_validation_ladder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "strategy.tsv"
            outdir = Path(tmp) / "ladder"
            write_tsv(input_path, [row(), row(gene_symbol="MOUSE", notes="mouse model needed")], SCREENING_STRATEGY_COLUMNS)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "run_validation_ladder.py"), "--input", str(input_path), "--outdir", str(outdir)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            output = read_tsv(outdir / "validation_ladder.tsv")
            self.assertGreaterEqual(len(output), 17)


if __name__ == "__main__":
    unittest.main()
