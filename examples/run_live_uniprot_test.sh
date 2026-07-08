#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p live_test_output
python scripts/fetch_uniprot_features.py \
  --input examples/input_candidates.tsv \
  --output live_test_output/uniprot_records.jsonl
