# Evidence Model

Every field that supports a decision must carry an evidence state.

## Evidence States

| State | Meaning |
|---|---|
| `confirmed` | Direct database, local, or literature evidence supports the exact claim. |
| `inferred` | Reasonable inference from sequence architecture or related evidence. |
| `missing` | Required evidence is unavailable. |
| `not_applicable` | The question does not apply to the candidate or modality. |
| `confirmed_local_xlsx` | Exact claim is supported by local user-provided tabular evidence. The enum label is retained for compatibility. |
| `inferred_from_local_xlsx` | Claim is inferred from local user-provided tabular evidence. The enum label is retained for compatibility. |

## Evidence Record Fields

Each JSONL record should include:

- `candidate_id`
- `gene_symbol`
- `claim`
- `evidence_type`
- `evidence_state`
- `source_name`
- `source_record`
- `notes`

## Non-Negative Missingness

Missing topology, expression, orthology, or drug evidence must not be reported as negative evidence. It is a stop condition or uncertainty state.
