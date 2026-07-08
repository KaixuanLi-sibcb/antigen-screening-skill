# Live ECD Validation

## Why Live ECD Validation Matters

Local user-provided evidence can be useful for reproducible pipeline checks, but ECD boundaries and human-mouse conservation should be cross-checked against authoritative protein and orthology sources before using them for construct or model-transfer decisions. The live-validation layer adds fixture-backed UniProt and Ensembl review while preserving the EvidenceRecord v2 provenance contract.

This layer validates evidence. It does not produce a final biological target call.

## UniProt Live Evidence Scope

The UniProt adapter is scoped to:

- accession lookup;
- gene-symbol plus species fallback lookup;
- reviewed/unreviewed status parsing;
- canonical sequence parsing;
- feature parsing for signal peptide, chain, domain, topological domain, and transmembrane segments;
- topology and ECD validation inputs;
- raw JSON hashing into EvidenceRecord v2.

If UniProt is unavailable, a failed fetch becomes `missing` or `error` EvidenceRecord v2 output. It is not interpreted as negative antigen evidence.

CI uses `tests/fixtures/live_uniprot/` and does not require network access.

## Ensembl Orthology Evidence Scope

The Ensembl adapter is scoped to:

- human gene symbol to mouse ortholog lookup;
- default source species `human`;
- default target species `mouse`;
- default target taxon `10090`;
- orthologue-only results;
- ambiguity reporting when multiple ortholog candidates are returned.

No HPA/GTEx, Open Targets, ChEMBL, or clinical evidence is fetched by this layer.

CI uses `tests/fixtures/live_ensembl/` and does not require network access. No-ortholog responses are `missing`; one-to-many responses emit a `conflict` EvidenceRecord instead of being silently resolved.

## ECD Sequence And Identity Review

The workflow extracts a human ECD sequence from UniProt-derived topology, maps the same human ECD coordinate range through Ensembl human/mouse peptide alignment to extract the mouse ECD sequence, computes pairwise ECD identity with a standard-library global-alignment fallback, and compares the result with a supplied local ECD identity value when provided.

`make live-ecd-fixture` covers the fixture-only path. `make all-checks-offline` is the clean-checkout target and does not require local user-provided inputs.

## Local Evidence vs Live Computed ECD Identity

The workflow keeps local and computed evidence separate:

- `local_tabular_ecd_identity`: local evidence field for a locally supplied ECD identity value;
- `live_computed_ecd_identity`: value computed from live or fixture-backed human/mouse ECD sequences.

The local value is not overwritten. If local and live/computed identity differ by more than the configured threshold, the workflow writes a conflict row rather than silently choosing one value.

## What Happens When Live And Local Evidence Conflict

Conflicts are written to machine-readable outputs:

```text
live_ecd_conflicts.tsv
evidence_conflicts.tsv
evidence_conflict_summary.json
```

Conflict examples:

- local ECD boundary differs from UniProt-derived boundary;
- local `ECD_identity` differs from computed ECD identity by more than the configured threshold;
- Ensembl returns multiple plausible mouse orthologs.

The local value is never overwritten. The computed value is written as `live_computed_ecd_identity`; local tabular evidence remains separate; the comparison is written as `ecd_identity_local_vs_computed`.

## What Gets Written To EvidenceRecord v2

The workflow writes:

- `confirmed_live` for successful live UniProt/Ensembl evidence;
- `confirmed_fixture` for fixture-backed CI evidence;
- `confirmed_local_xlsx` for local tabular evidence, retaining the schema enum name for compatibility;
- `computed` source authority for pairwise identity values;
- `missing` or `error` for unavailable or failed live evidence;
- `conflict` records when values conflict.

`confirmed_live` requires source URL, source version, retrieval timestamp, and raw-response SHA-256.

## Why CI Uses Fixtures Or Cassettes

CI must not depend on public API availability, rate limits, or response drift. Tests use local fixture JSON that mirrors UniProt/Ensembl response shapes. Live API calls are optional local validation, not required CI checks.

## What This Still Does Not Prove Biologically

Live ECD validation does not prove surface abundance, tissue safety, therapeutic window, clinical evidence, binding, expression yield, or animal cross-reactivity. HPA/GTEx normal-tissue evidence, Open Targets/ChEMBL evidence, and later wet-lab validation remain separate steps.
