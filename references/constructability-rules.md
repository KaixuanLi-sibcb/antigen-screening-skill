# Constructability Rules

## Constructability Gate

- `pass`: continuous ECD suitable for soluble recombinant antigen.
- `partial`: short ECD, long multi-domain ECD, secreted-control use, or cell-display fallback.
- `fail`: intracellular/nuclear protein, no ECD, or discontinuous multi-pass topology unsuitable for soluble ECD.

## Recommended Strategies

| Case | Strategy |
|---|---|
| 150-500 aa continuous ECD | monomeric His-Avi and optional Fc |
| 50-149 aa ECD | Fc, Avi multimer, or scaffold display |
| >500 aa ECD | full ECD plus domain split panel |
| multi-pass | full-length cell display; avoid artificial soluble ECD |
| secreted protein | soluble protein control or antibody antigen, not CAR surface target |
| intracellular/nuclear | no ECD construct |

## Optional Local Construct Fields

Use supplied ECD coordinates, ECD length, coding sequence, primer fields, or stock coordinates as construct/logistics evidence only when they are present and provenance is recorded. Missing primer fields are warnings unless the candidate is otherwise construct-ready.
