from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ValidateSkillTest(unittest.TestCase):
    def test_validate_skill_script_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_skill.py"), "--skill-dir", str(ROOT)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["status"], "pass")


if __name__ == "__main__":
    unittest.main()
