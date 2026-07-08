# Decision Gates

Scores are used only for tie-breaking after gates are evaluated. A failed gate is not rescued by a high score.

## Gate 1. Antigen Accessibility

- `pass`: extracellular, membrane-accessible, secreted, GPI-anchored, or extracellular matrix evidence supports antigen access.
- `fail`: intracellular, nuclear, cytosolic, mitochondrial, or no extracellular region for a surface-targeting modality.
- `uncertain`: topology missing or isoform conflicts change ECD/TM architecture.

## Gate 2. Disease Relevance

- `pass`: disease, tumor, cell-state, lineage, local omics, or user-provided evidence is available.
- `uncertain`: only a gene list is available.
- `fail`: evidence explicitly indicates no disease relevance for the requested context.

## Gate 3. Normal Tissue Risk

Classify as `low`, `medium`, `high`, or `unknown`.

High-risk tissues include heart, CNS, lung epithelium, kidney, liver, endothelium, hematopoietic progenitors, and essential immune compartments depending on modality.

## Gate 4. Mouse-Model Transferability

- `pass`: human-mouse ECD identity is above the configured threshold.
- `uncertain`: no ortholog, no ECD sequence, or unavailable ECD identity.
- `fail`: ECD identity is below the configured threshold.
- `not_applicable`: no mouse-model claim is requested.

The default threshold is configurable and should not be hard-coded in the reasoning.

When a locally supplied ECD identity value is available, use it for this gate only if provenance is recorded. Do not substitute whole-protein `seq_identity`.

## Gate 5. Constructability

- `pass`: clean soluble ECD construct is possible.
- `partial`: cell-display, domain-fragment, Fc/multimer, or special construct strategy is needed.
- `fail`: no extracellular region or discontinuous multi-pass topology is unsuitable for soluble ECD.

## Priority Calls

- `go`: accessibility and modality are compatible, no unresolved stop condition.
- `conditional`: plausible but requires follow-up data or special construct handling.
- `no_go`: gate failure for requested use.
- `control_or_not_applicable`: useful as a control or non-surface antigen, but not a therapeutic surface target for the requested modality.
