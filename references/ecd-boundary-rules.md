# ECD Boundary Rules

## Boundary Priority

1. Reviewed explicit extracellular topological-domain feature.
2. Chain/propeptide annotation combined with topology.
3. Single-pass inference from signal peptide and TM.
4. Secreted mature chain for soluble antigen or control work.
5. Multi-pass extracellular loops as loop-level or cell-display only.

## Mature Soluble ECD Rules

- Do not include signal peptide in the mature ECD.
- Do not include TM helix.
- Do not include cytoplasmic tail.
- Do not merge discontinuous loops into one artificial ECD unless clearly labeled.

## Confidence

| Confidence | Meaning |
|---|---|
| `high` | explicit reviewed ECD/topological domain |
| `medium` | consistent reviewed signal peptide and TM inference |
| `low` | unreviewed or weak inference |
| `none` | no usable boundary |
