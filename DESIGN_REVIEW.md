# Design Review

This public release separates the antigen-screening workflow into four layers:

## A. Target Discovery

Candidate genes or proteins can come from user-provided lists, marker tables, DEG tables, proteomics surfaceome tables, or manual target lists. Discovery evidence is treated as context, not as proof of surface accessibility.

## B. Antigen Eligibility

Eligibility asks whether a candidate is plausibly extracellular, secreted, or membrane accessible. The workflow distinguishes type I, type II, multi-pass membrane proteins, GPI anchors, secreted ligands, extracellular matrix proteins, and intracellular/nuclear/cytosolic negative controls.

## C. Therapeutic Modality Suitability

The workflow evaluates antibody, CAR, ADC, bispecific, and soluble-ECD screening contexts separately. A candidate can be reasonable for one modality and poor for another.

## D. Construct Engineering

Construct planning checks whether a recombinant antigen can be made from a clean soluble ECD, Fc fusion, AviTag/His tag format, multimer display, full-length cell display, or fallback display system. It records signal peptide, transmembrane, cytoplasmic tail, disulfide, glycosylation, cysteine-rich, multi-pass, and isoform risks.

## Problems Fixed From Earlier Designs

- Mixed target discovery, antigen eligibility, therapeutic modality, and construct engineering into one broad score.
- Treated missing evidence as if it were negative evidence.
- Risked using RNA expression as a proxy for surface protein evidence.
- Did not keep ECD identity separate from whole-protein identity.
- Did not make evidence provenance and conflict states machine-readable.
- Did not provide enough fixture-based checks for offline validation.
- Contained private-data workflow references that are intentionally excluded from the public release.
