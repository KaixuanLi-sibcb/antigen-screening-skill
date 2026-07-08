# Workflow

## 1. Input Audit

Normalize all candidates into a TSV-compatible table with at least `gene_symbol`, `species`, `modality`, `disease_context`, and `user_evidence`.

## 2. Target Discovery Boundary

If the input is scRNA, DEG, proteomics, or literature output, treat it as a candidate source. Do not call it an antigen until topology and localization are reviewed.

## 3. Antigen Eligibility

Read UniProt-like features and classify surface accessibility:

- single-pass membrane
- multi-pass membrane
- GPI anchored
- secreted or soluble extracellular
- extracellular matrix
- intracellular, nuclear, cytosolic, mitochondrial, or unknown

## 4. ECD Boundary Extraction

Prefer explicit extracellular topological domains. Infer boundaries only when signal peptide and TM evidence support it. Mark inference clearly.

## 5. Modality Fit

Evaluate antibody, CAR-T, ADC, bispecific, and soluble ECD screen separately. Do not merge them into one generic target suitability call.

## 6. Cross-Species Review

For mouse models, compare human and mouse ECD identity. Use a configurable threshold and report unavailable orthology as uncertain.

## 7. Optional Live ECD Validation

When explicitly requested, validate ECD evidence against UniProt and Ensembl. Keep locally supplied ECD identity and live/computed ECD identity as separate EvidenceRecord v2 rows. Live failures are `missing` or `error`, not negative evidence. CI must use fixture/cassette evidence rather than mandatory network access.

## 8. Construct Engineering

Remove signal peptide from mature ECD coordinates, exclude TM/cytoplasmic tail from soluble ECD constructs, and flag discontinuous or complex ECD architecture.

## 9. Reporting

Create machine-readable TSV/JSON files and one human-readable report. Include missing evidence and stop conditions.
