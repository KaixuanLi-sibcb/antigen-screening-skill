# Coverage Diagnostics

Coverage diagnostics explain why evidence is `missing`, `unknown`, `not_applicable`, conflicted, or errored. This layer does not add new biological ranking logic and does not run production HPA/GTEx, Open Targets, ChEMBL, ClinicalTrials, or batch live ECD adapters.

## Purpose

The diagnostic layer separates:

- identifier mapping gaps;
- ambiguous gene alias or accession mapping;
- adapters that are implemented but not run;
- adapters that are planned but not implemented;
- source records that are unavailable;
- source fields that are blank;
- query or network errors;
- modality-specific non-applicability;
- coverage that is pending for a later step.

Missing evidence must never be interpreted as negative evidence. Missing normal-tissue evidence is not low risk. Missing drug evidence is not no druggability. Missing HPA evidence is not low expression.

## Outputs

Step 4 writes five machine-readable or report artifacts:

```text
coverage_diagnostics.tsv
id_mapping_rescue.tsv
missingness_reason_summary.json
adapter_readiness_matrix.tsv
coverage_report.md
```

## Missing Reason Vocabulary

Allowed missing-reason values:

```text
id_mapping_missing
id_mapping_ambiguous
source_not_configured
adapter_not_implemented
adapter_not_run
source_record_missing
source_field_missing
query_error
network_unavailable
fixture_only
not_applicable_to_modality
conflicting_sources
insufficient_topology
insufficient_ecd_boundary
insufficient_orthology
private_source_absent
coverage_pending
unknown
```

## ID Rescue

The ID rescue table records how each candidate was resolved or why it could not be resolved. Supported statuses include exact symbol resolution, alias resolution, UniProt-first resolution, Ensembl resolution, ambiguous alias mapping, conflicts, missing identifiers, not checked, and errors.

The rescue output should guide the next concrete action: add a UniProt accession, add an Ensembl gene ID, add HGNC mapping, manually review aliases, or mark the field as not applicable.

## Adapter Readiness

The adapter readiness matrix documents which evidence layers are implemented, fixture-backed, local-only, live-optional, not implemented, planned, deprecated, or not applicable.

This keeps downstream interpretation honest. For example, HPA/GTEx and Open Targets/ChEMBL can be marked `adapter_not_implemented` or `not_run` without implying that normal-tissue risk is low or that no drug evidence exists.

## EvidenceRecord v2 Compatibility

Coverage diagnostics are compatible with EvidenceRecord v2:

- missing values remain `evidence_status=missing`;
- adapter failures use `evidence_status=error`;
- pending adapters are represented as `missing` or `not_applicable` with a clear `failure_mode`;
- local tabular evidence remains `confirmed_local_xlsx` or `inferred_local_xlsx`;
- fixture evidence remains `confirmed_fixture`;
- future live evidence must use `confirmed_live` or `inferred_live` only with complete source metadata.

## Interpretation By Modality

- CAR-T and T-cell engager: missing normal-tissue evidence is a critical data gap.
- ADC: missing normal-tissue evidence is a hold unless the target is exploratory only.
- Soluble ECD screen: missing normal-tissue evidence affects target interpretation, not necessarily construct feasibility.
- Screening antigen: missing normal-tissue evidence does not block antigen-material preparation, but blocks therapeutic safety claims.
