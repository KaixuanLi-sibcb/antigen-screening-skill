from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antigen_screening.antigen_readiness import READINESS_COLUMNS
from antigen_screening.io import read_tsv, write_tsv
from antigen_screening.screening_strategy import strategy_for_row


def row(**updates: str) -> dict[str, str]:
    base = {column: "" for column in READINESS_COLUMNS}
    base.update(
        {
            "candidate_id": "C1",
            "gene_symbol": "TEST",
            "antigen_readiness": "ready",
            "antigen_accessibility": "surface_single_pass",
            "readiness_flags": "",
            "stop_condition": "",
        }
    )
    base.update(updates)
    return base


class ScreeningStrategyTest(unittest.TestCase):
    def test_clean_ecd_uses_soluble_ecd(self) -> None:
        plan = strategy_for_row(row())
        self.assertEqual(plan["primary_strategy"], "soluble_ecd")
        self.assertEqual(plan["secondary_strategy"], "avitag_biotin_multimer")

    def test_multi_pass_uses_cell_display_and_membrane_display(self) -> None:
        plan = strategy_for_row(row(antigen_readiness="conditional", readiness_flags="multi_pass_discontinuous_ecd;cell_display_fallback"))
        self.assertEqual(plan["primary_strategy"], "full_length_cell_display")
        self.assertEqual(plan["secondary_strategy"], "vlp_nanodisc_membrane_display")

    def test_short_ecd_uses_multimer_or_fragment(self) -> None:
        plan = strategy_for_row(row(antigen_readiness="conditional", readiness_flags="short_ecd"))
        self.assertEqual(plan["primary_strategy"], "avitag_biotin_multimer")
        self.assertEqual(plan["secondary_strategy"], "peptide_domain_fragment")

    def test_gpi_and_secreted_cases_are_handled(self) -> None:
        gpi = strategy_for_row(row(antigen_readiness="conditional", readiness_flags="gpi_anchor"))
        self.assertEqual(gpi["secondary_strategy"], "full_length_cell_display")
        secreted = strategy_for_row(row(antigen_readiness="conditional", readiness_flags="secreted_soluble_antigen"))
        self.assertEqual(secreted["primary_strategy"], "soluble_ecd")
        self.assertEqual(secreted["secondary_strategy"], "fc_dimer")

    def test_not_ready_is_not_recommended(self) -> None:
        plan = strategy_for_row(row(antigen_readiness="not_ready", readiness_flags="accessibility_fail", stop_condition="no ECD"))
        self.assertEqual(plan["primary_strategy"], "not_recommended")
        self.assertEqual(plan["not_recommended_reason"], "no ECD")

    def test_cli_writes_strategy_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "readiness.tsv"
            outdir = Path(tmp) / "strategy"
            write_tsv(input_path, [row(), row(gene_symbol="MP", antigen_readiness="conditional", readiness_flags="multi_pass_discontinuous_ecd")], READINESS_COLUMNS)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "run_screening_strategy.py"), "--input", str(input_path), "--outdir", str(outdir)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            output = read_tsv(outdir / "screening_strategy_plan.tsv")
            self.assertEqual(len(output), 2)


if __name__ == "__main__":
    unittest.main()
