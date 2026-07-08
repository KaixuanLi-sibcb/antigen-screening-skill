#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/run_smoke_test.py --skill-dir . --outdir smoke_test_output
