# Roadmap

## Milestone 1 - Provenance Hardening

- Keep EvidenceRecord v2 validation required for all evidence-producing workflows.
- Extend conflict summaries with source-priority review views.
- Add provenance dashboards for local tabular evidence, live public evidence, computed values, and missing states.
- Add coverage diagnostics for missing-evidence reasons, ID rescue status, and adapter readiness before expanding public evidence adapters.

## Milestone 2 - Public Evidence Adapters

- Add Open Targets and ChEMBL modality-evidence adapters.
- Add live HPA/GTEx normal-tissue batch validation with cacheable provenance.
- Harden Ensembl/MGI orthology handling for one-to-many mappings and isoform-sensitive cases.
- Expand live ECD validation into cassette-backed batch mode.

## Milestone 3 - Construct Engineering

- Add isoform-aware ECD boundary resolution.
- Add domain-split recommendations for very large ECDs.
- Add multi-pass display templates for cell display, VLP, nanodisc, and membrane-display workflows.

## Milestone 4 - Review And Reporting

- Add summary dashboards for fixture regression checks.
- Add report sections for provenance conflicts, missing evidence, and modality-specific experimental next steps.
- Keep CI fixture-only and privacy-safe across Python 3.10-3.12.
