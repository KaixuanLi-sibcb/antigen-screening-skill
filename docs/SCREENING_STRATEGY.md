# Screening Strategy Planner

The screening strategy planner selects practical antigen formats for antibody discovery and binding-validation experiments. It is downstream of accessibility, ECD boundary, antigen readiness, and constructability evidence.

It does not rank therapeutic targets and does not claim that a format will express successfully.

Implementation: `scripts/antigen_screening/screening_strategy.py` and `scripts/run_screening_strategy.py` read `antigen_readiness_table.tsv` and write `screening_strategy_plan.tsv`.

Fixture target: `make screening-strategy-fixture`.

## Strategy Options

- `soluble_ecd`: clean continuous ECD suitable for monomeric soluble screening antigen.
- `fc_dimer`: soluble ECD likely benefits from dimerization or increased stability.
- `avitag_biotin_multimer`: clean ECD suitable for biotinylated multimer screening.
- `full_length_cell_display`: native full-length display preferred, often for multi-pass or membrane-proximal targets.
- `vlp_nanodisc_membrane_display`: membrane context is important or multi-pass topology prevents clean soluble ECD.
- `peptide_domain_fragment`: full ECD is difficult, but a defined extracellular domain or loop may be screened cautiously.
- `not_recommended`: intracellular/nuclear, no ECD, failed accessibility, or no credible antigen material.

## Decision Notes

- Soluble ECD should remove signal peptide, transmembrane segment, and cytoplasmic tail.
- GPI-anchored proteins can often use soluble ECD after anchor removal, but membrane display may better preserve context.
- Secreted antigens can be screened as soluble proteins but should be flagged for CAR or ADC mismatch unless a surface-associated form is documented.
- Multi-pass proteins should default to cell display, VLP, nanodisc, membrane display, or loop/domain fragments.
- Short ECDs often need multimerization or peptide/domain strategy.
- Long, cysteine-rich, disulfide-rich, or heavily glycosylated ECDs require expression-risk flags.
