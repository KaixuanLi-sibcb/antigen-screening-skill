# Privacy And Data Governance

This repository is designed as a public, privacy-safe workflow release. Source code, fixtures, schemas, and documentation are versioned. Private source files and generated outputs are intentionally excluded.

## Never Commit

- Private source files.
- Local tabular evidence folders.
- Fixture regression output folders.
- Fixture smoke output folders.
- Live-validation output folders.
- Coverage diagnostic output folders.
- Installed-copy output folders.
- Distribution archives.
- Python caches, test caches, and backup folders.

## Required Privacy Checks

```bash
make privacy-check
git ls-files "*.xlsx"
git ls-files | grep -E '(^local_data/|^real_data_output/|^coverage_output/|^smoke_test_output/|^live_validation_output/|^dist/|\.xlsx$)' || true
```

The tracked-file checks must return no private source files or generated-output paths before pushing.

## Repository Visibility

The public repository must be created from a sanitized, no-history snapshot. Do not make a private working repository public until its full history has been audited.

## CI Boundary

CI must use fixture and schema tests only. It must not require local user-provided inputs, generated outputs, live HPA/GTEx access, Open Targets, ChEMBL, or batch live ECD validation.

Coverage diagnostics generated under `coverage_output/` are local artifacts and must remain untracked.
