# Antibody Validation Ladder

The validation ladder is a staged plan for confirming that antibody hits bind the intended antigen in biologically relevant contexts.

It is a planning artifact, not evidence that validation has already been completed.

Implementation: `scripts/antigen_screening/validation_ladder.py` and `scripts/run_validation_ladder.py` read `screening_strategy_plan.tsv` and write `validation_ladder.tsv`.

Fixture target: `make validation-ladder-fixture`.

## Required Validation Layers

- orthogonal validation: use a second assay or antigen format;
- genetic validation: knockout, knockdown, or perturbation should reduce binding when feasible;
- independent reagent validation: compare independent antibodies, clones, or binder formats;
- tagged protein validation: tagged overexpression or rescue confirms target-dependent binding;
- flow or cell binding validation: test binding on target-positive and target-negative cells;
- loss-of-binding validation: knockout or knockdown should reduce signal;
- gain-of-binding validation: overexpression should increase signal;
- cross-species binding: required when mouse-model transferability is claimed.

## Optional Validation Layers

- immunocapture-MS to confirm target identity of binding reagent;
- orthogonal surface proteomics for unexpected binders;
- epitope-domain mapping for multi-domain ECDs;
- glycoform or isoform review for heavily modified ECDs.

## Stop Conditions

Do not mark a binder as target-validated when:

- only recombinant ECD binding is shown;
- only RNA expression supports target presence;
- knockout or knockdown loss-of-binding is unavailable and no orthogonal substitute is provided;
- cross-species binding is assumed from whole-protein identity rather than ECD identity.
