# Output Format

Each run must create TSV/JSON files and a Markdown report.

## `antigen_screening_table.tsv`

Machine-readable candidate table. Required columns are listed in `schemas/candidate_output.columns.tsv`.

Key fields include:

- gate calls: `accessibility_gate`, `disease_relevance_gate`, `mouse_model_transferability_gate`, `constructability_gate`, `modality_gate`
- evidence states: `accessibility_evidence_state`, `ecd_evidence_state`, `disease_evidence_state`, `normal_tissue_risk_evidence_state`, `orthology_evidence_state`, `modality_evidence_state`
- ECD fields: `ecd_region`, `ecd_length`, `ecd_boundary_confidence`
- decision fields: `risk_flags`, `tie_break_score`, `priority_call`, `decision_rationale`, `missing_evidence`

## `evidence_records.jsonl`

One EvidenceRecord v2 JSON object per evidence claim. See `schemas/evidence_record.schema.json`.

Required provenance fields include `record_version`, candidate identifiers, source metadata, `raw_response_sha256`, `evidence_status`, `source_authority_level`, `conflict_status`, and `failure_mode`.

`missing` records must not carry fake evidence values, and `confirmed_live` records require source URL, source version, retrieval timestamp, and raw-response hash.

## `evidence_conflicts.tsv`

One row per detected evidence conflict. Empty conflict reports still write the header.

## `evidence_conflict_summary.json`

JSON summary with `records_checked`, `conflict_count`, and conflict status counts.

## `risk_flags.tsv`

One row per risk flag with `gene_symbol`, `flag_type`, `severity`, `evidence`, and `action`.

## `construct_plan.tsv`

One row per candidate. For failed or uncertain targets, use stop-condition recommendations instead of forcing an ECD construct.

## `antigen_readiness_table.tsv`

Step 3 readiness output. It records `ready`, `conditional`, `not_ready`, or `missing_evidence` calls plus readiness flags and screening material recommendations.

## `antigen_readiness_summary.json`

JSON summary with candidate count, readiness call counts, flag counts, and output paths.

## `normal_tissue_risk.tsv`

Step 3 HPA normal-tissue risk output. It records risk class, high-risk tissue flags, separate RNA/protein evidence levels, and missing evidence.

## `hpa_evidence_records.jsonl`

EvidenceRecord v2 JSONL from the HPA adapter. RNA and protein evidence are separate evidence types, and blank HPA values are `missing`.

## `normal_tissue_risk_summary.json`

JSON summary with candidate count, risk class counts, evidence-record count, and output paths.

## `screening_strategy_plan.tsv`

Step 3 antibody screening material plan. Strategy options include soluble ECD, Fc-dimer, AviTag-biotin multimer, full-length cell display, VLP/nanodisc/membrane display, peptide/domain fragment, and not recommended.

## `screening_strategy_summary.json`

JSON summary with candidate count, primary strategy counts, and output paths.

## `validation_ladder.tsv`

Step 3 antibody validation planning table. It includes orthogonal validation, genetic validation, independent reagent validation, tagged protein validation, flow/cell binding validation, knockout/knockdown loss-of-binding, overexpression gain-of-binding, optional immunocapture-MS, and cross-species binding when mouse models are claimed.

## `validation_ladder_summary.json`

JSON summary with candidate count, validation-stage counts, and output paths.

## Coverage Diagnostics Outputs

Step 4 writes:

```text
coverage_diagnostics.tsv
id_mapping_rescue.tsv
missingness_reason_summary.json
adapter_readiness_matrix.tsv
coverage_report.md
```

These artifacts explain why evidence is missing or unknown. They distinguish ID mapping failure, ambiguous mapping, adapter not implemented, adapter not run, source unavailable, source field missing, query error, not applicable, and coverage pending. Missing evidence must not be interpreted as negative evidence.

## Report Priority Outputs

Step 5 report-priority ranking writes:

```text
report_priority/report_priority_table.tsv
report_priority/report_priority_summary.json
report_priority/report_priority_report.md
report_priority/report_priority_workbook.xlsx
```

The report must record `identity_preference`. For antibody-screening ranking, use `low_for_antibody_screening`; in that mode low human-mouse ECD identity is favorable and the upstream mouse-model transferability gate is retained only as audit context.

## `report.md`

Human-readable summary in Chinese. It must list passed, failed, uncertain, and missing-evidence cases.

## Live ECD Validation Outputs

Step 2 live ECD validation writes these optional artifacts when the workflow is explicitly invoked:

```text
live_validation_output/<candidate>/live_ecd_evidence_records.jsonl
live_validation_output/<candidate>/live_ecd_conflicts.tsv
live_validation_output/<candidate>/live_ecd_summary.json
```

The live ECD evidence JSONL includes separate records for:

```text
uniprot_accession
uniprot_sequence
uniprot_topology_features
ensembl_orthology_lookup
live_human_ecd_boundary
live_human_ecd_sequence_length
live_mouse_ecd_sequence_length
live_computed_ecd_identity
local_tabular_ecd_identity
ecd_identity_local_vs_computed
```

Conflict rows are written when local and computed ECD identity differ beyond the configured tolerance:

```text
live_validation_output/<candidate>/live_ecd_conflicts.tsv
```

These generated outputs are ignored by Git. CI uses fixture/cassette mode and does not require live network access.
