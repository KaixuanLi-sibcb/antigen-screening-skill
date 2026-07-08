# Evidence Levels

## EvidenceRecord v2 Statuses

| State | Use |
|---|---|
| `confirmed_live` | exact claim directly supported by a live source; requires source URL, source version, retrieval timestamp, and raw-response hash |
| `confirmed_local_xlsx` | exact claim directly supported by local tabular evidence; enum label retained for compatibility |
| `confirmed_fixture` | exact claim directly supported by offline fixture files |
| `inferred_live` | claim inferred from compatible live evidence |
| `inferred_local_xlsx` | claim inferred from local tabular grouping, topology, or location text; enum label retained for compatibility |
| `missing` | evidence unavailable |
| `not_applicable` | claim does not apply |
| `conflict` | evidence conflicts across sources or versions |
| `error` | adapter or parser failed |

Legacy states `confirmed`, `inferred`, and `inferred_from_local_xlsx` may appear in gate-level columns for backward compatibility, but `evidence_records.jsonl` must use EvidenceRecord v2 statuses.

## Source Authority Levels

| Level | Use |
|---|---|
| `local_lab` | local user-provided or lab-curated evidence |
| `fixture` | offline smoke-test fixture |
| `curated_database` | curated database evidence |
| `public_database` | public database evidence |
| `computed` | computed adapter result |
| `unknown` | authority unavailable |

## Required Practice

Every gate and construct field must expose uncertainty. Do not collapse `missing` into `fail` unless the requested claim requires proof and the absence of proof is a stop condition.

For EvidenceRecord v2:

- `record_version` must be `2.0`.
- `missing` must not carry a fake `evidence_value`.
- `not_applicable` is a context/modality state, not evidence negativity.
- `confirmed_live` requires provenance metadata.
- Live UniProt or Ensembl fetch failures must be `missing` or `error`; they do not imply the antigen is negative.
- Local tabular `ECD_identity`, live/computed ECD identity, and fixture identities are separate evidence claims unless an explicit comparison workflow links them.
- Conflicts must record `conflict_status` and `failure_mode`.

## Missing Reason Vocabulary

Coverage diagnostics use controlled missing reasons:

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

These reasons explain evidence coverage. They do not make missing evidence negative.
