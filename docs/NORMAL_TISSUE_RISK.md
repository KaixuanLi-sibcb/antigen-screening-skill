# Normal-Tissue Risk

Normal-tissue risk is a modality-aware safety triage layer. It is not a toxicity prediction and does not replace experimental safety work.

Implementation: `scripts/antigen_screening/hpa_adapter.py` and `scripts/run_hpa_normal_tissue_risk.py` provide a fixture-backed, adapter-ready interface. CI uses `tests/fixtures/hpa/` and does not require live HPA access.

Fixture target: `make hpa-fixture-smoke`.

## Evidence Separation

HPA-style evidence must keep these evidence types separate:

- RNA tissue expression;
- protein immunohistochemistry or protein-level evidence;
- single-cell or compartment annotation when available;
- missing or blank values.

RNA evidence must not be treated as surface protein evidence. Blank tissue values must be recorded as `missing`, not as `low`.

## Risk Classes

- `low`: low or absent normal expression in high-risk tissues with protein-level support.
- `medium`: expression in non-critical tissues, weak or uncertain protein evidence, or modality-dependent immune-compartment risk.
- `high`: expression in high-risk tissues relevant to the intended modality.
- `unknown`: normal-tissue evidence is absent, incomplete, or not interpretable.

## High-Risk Tissue Flags

The adapter explicitly flags:

- heart;
- CNS or brain;
- lung epithelium;
- kidney;
- liver;
- endothelium;
- bone marrow;
- immune progenitor or essential immune compartment.

## EvidenceRecord v2

Normal-tissue outputs use EvidenceRecord v2:

- successful fixture lookup: `confirmed_fixture`;
- successful live lookup: `confirmed_live`;
- blank or missing tissue value: `missing`;
- parse or API failure: `error`;
- conflicting RNA/protein interpretation: `conflict`.

Live HPA access remains optional. CI uses local fixtures only, and this adapter is not currently a complete live HPA batch validator for the local candidate panel.
