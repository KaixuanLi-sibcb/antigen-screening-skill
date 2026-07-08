# Topology Interpretation

## Surface Classes

- `surface_single_pass`: one TM and extracellular domain evidence or supported inference.
- `surface_multi_pass`: more than one TM; surface accessible but soluble ECD may be discontinuous.
- `gpi_anchored`: extracellular protein linked by GPI anchor.
- `secreted`: soluble extracellular protein, not automatically a cell-surface target.
- `extracellular_matrix`: extracellular but modality-specific.
- `intracellular`: nuclear, cytosolic, mitochondrial, ER-only, or no extracellular access.
- `unknown`: insufficient evidence.

## Common Pitfalls

- Treating signal peptide alone as membrane anchoring.
- Treating secreted plasma proteins as CAR targets.
- Ignoring cytoplasmic topological domains.
- Treating multi-pass receptors as simple soluble ECD antigens.
