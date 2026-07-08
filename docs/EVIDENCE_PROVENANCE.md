# Evidence Provenance

## Why Provenance Matters

Antigen screening decisions mix topology, ECD boundaries, mouse-model transferability, constructability, normal-tissue risk, and modality fit. Without a stable evidence contract, later live adapters can overwrite or blur local evidence, fixture evidence, missing evidence, and conflicting evidence.

EvidenceRecord v2 makes each claim auditable. It records the source, source authority, source version, query, adapter, raw-response hash, confidence, and conflict state for every evidence row.

## EvidenceRecord v2 Fields

Required fields:

```text
record_version
candidate_id
gene_symbol
species
uniprot_accession
ensembl_gene_id
evidence_type
evidence_value
normalized_value
evidence_status
source_name
source_authority_level
source_url
source_version
retrieved_at
query
adapter_name
adapter_version
raw_response_sha256
confidence
conflict_status
failure_mode
license_note
```

`record_version` is fixed to `2.0`.

## Evidence Status Enum

Allowed values:

| Status | Meaning |
|---|---|
| `confirmed_live` | Directly supported by a live source; requires source URL, version, retrieval time, and raw-response hash. |
| `confirmed_local_xlsx` | Directly supported by local tabular evidence. The enum name is retained for backward-compatible schema validation. |
| `confirmed_fixture` | Directly supported by offline fixture evidence. |
| `inferred_live` | Inferred from live evidence. |
| `inferred_local_xlsx` | Inferred from local tabular evidence text, grouping, or derived fields. The enum name is retained for backward-compatible schema validation. |
| `missing` | Required evidence is unavailable. |
| `not_applicable` | The claim does not apply to the requested modality or context. |
| `conflict` | Evidence conflicts across records. |
| `error` | Adapter or parsing error. |

## Source Authority Levels

Allowed values:

| Level | Meaning |
|---|---|
| `local_lab` | Local user-provided or lab-curated evidence. |
| `fixture` | Offline test fixture. |
| `curated_database` | Curated source such as future drug or target databases. |
| `public_database` | Public source such as future UniProt, Ensembl, HPA, or GTEx adapters. |
| `computed` | Computed value from an adapter or algorithm. |
| `unknown` | Source authority not available. |

## Missing Is Not Negative

`missing` means evidence was unavailable. It does not mean the target is negative, unsafe, absent, or biologically invalid.

Rules:

- `missing` records must not carry `evidence_value` or `normalized_value`.
- Empty cells, blank annotations, and unavailable live adapters become `missing`.
- `not_applicable` is used for modality/context mismatch, not negative evidence.
- Gate failures can still occur when a claim requires evidence and evidence is missing, but the evidence record itself remains `missing`.

## Conflict Handling

`evidence_conflicts.tsv` and `evidence_conflict_summary.json` are emitted for screening runs. Current conflict detection groups records by `candidate_id` and `evidence_type`.

Current support:

- local tabular evidence vs fixture value conflicts
- local tabular evidence vs future live placeholder source conflicts

The conflict report is written even when no conflicts are found.

## Local Evidence vs Fixture vs Future Live Evidence

Fixture mode:

- source name: `fixture_uniprot_like_json`
- status: `confirmed_fixture` for supported values, `missing` for unavailable values

Local tabular evidence mode:

- source names use adapter-specific local tabular identifiers
- status: `confirmed_local_xlsx`, `inferred_local_xlsx`, or `missing`
- raw-response hash is derived from local evidence payloads and any available local source-file hashes

Live or future live mode:

- implemented live adapters write `confirmed_live`, `missing`, `error`, or `conflict` records
- pending HPA/GTEx, Open Targets/ChEMBL, and expanded Ensembl/MGI evidence is represented as `missing` with explicit placeholder source names

## How To Validate Evidence Records

```bash
python scripts/validate_evidence_records.py \
  --input smoke_test_output/evidence_records.jsonl \
  --schema schemas/evidence_record.schema.json
```

The validator checks JSONL parsing, required fields, enum values, fixed `record_version`, missing-value rules, live metadata rules, local/fixture source-name rules, and conflict metadata rules.

## What This Does Not Yet Prove Biologically

EvidenceRecord v2 makes the workflow auditable. It does not prove surface expression, safety, clinical relevance, mouse cross-reactivity, or construct expression. Live HPA/GTEx, Open Targets/ChEMBL, expanded Ensembl/MGI, and batch ECD-alignment adapters remain pending.
