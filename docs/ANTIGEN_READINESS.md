# Antigen Readiness Gate

Antigen readiness is a middle layer between antigen accessibility and final prioritization. It asks whether a candidate is ready for antigen production, antibody screening, or display-based fallback planning based on the evidence currently available.

It is not biological validation and it is not a final therapeutic target ranking.

Implementation: `scripts/antigen_screening/antigen_readiness.py` and `scripts/run_antigen_readiness.py` read an existing `antigen_screening_table.tsv` and write `antigen_readiness_table.tsv` plus `antigen_readiness_summary.json`.

Fixture target: `make antigen-readiness-fixture`.

## Inputs

- antigen accessibility gate;
- ECD boundary and ECD length;
- topology flags;
- isoform ambiguity;
- constructability gate;
- glycosylation, cysteine, and disulfide annotations when available;
- modality and mouse-model intent;
- EvidenceRecord v2 provenance.

## Readiness Calls

- `ready`: surface or soluble antigen evidence is compatible with a clear screening-material strategy.
- `conditional`: antigen is plausible but requires fallback display, domain-fragment design, isoform review, or additional evidence.
- `not_ready`: intracellular or nuclear localization, no extracellular region, failed accessibility, or no feasible screening material.
- `missing_evidence`: readiness cannot be assessed because required topology or ECD evidence is missing.

## Required Flags

Readiness output preserves separate flags for:

- clean soluble ECD;
- multi-pass or discontinuous ECD;
- secreted soluble antigen;
- GPI anchor;
- short ECD;
- long ECD;
- cysteine-rich or disulfide-rich ECD;
- glycosylation-rich ECD;
- isoform ambiguity;
- cell-display fallback.

## Stop Conditions

Stop before recommending soluble ECD screening when:

- accessibility gate fails for a surface-targeting modality;
- ECD boundary is missing;
- ECD is discontinuous and no display fallback is acceptable;
- isoforms may change the ECD or transmembrane architecture;
- normal-tissue evidence is required for the modality and is absent.

## Evidence Rules

- Missing topology is `missing_evidence`, not a negative antigen call.
- Short or long ECD is a construct risk, not an automatic target failure.
- Secreted proteins can be soluble antigen controls or antibody-screening antigens, but should not be promoted as CAR or ADC surface targets without cell-surface evidence.
- Multi-pass proteins usually require full-length cell display, VLP, nanodisc, membrane display, or loop/domain fragments.
