# Feasibility Matrix

This public release is designed to run offline with fixtures and optional local live checks. Missing evidence is represented explicitly and must not be interpreted as negative evidence.

| Step | Required input | External data | Offline? | Live? | Failure mode | Stop condition | Fallback | Smoke-test coverage |
|---|---|---|---|---|---|---|---|
| Gene symbol normalization | candidate TSV | optional curated alias map | yes | no | missing or ambiguous identifier | no candidate ID or symbol | mark `id_mapping_missing` or `id_mapping_ambiguous` | unit tests |
| UniProt feature fetch | symbol or accession | UniProt REST | fixture yes | optional | network/query/error or missing topology | no usable feature record when live validation required | write `missing` or `error` EvidenceRecord | fixture live-ECD test |
| ECD boundary extraction | UniProt-like feature record | none | yes | no | missing topology, multi-pass ambiguity | intracellular-only candidate for ECD construct | infer cautiously or mark missing | topology/ECD tests |
| Isoform ambiguity detection | feature evidence | optional isoform metadata | partial | optional | isoform alters ECD/TM | ambiguous construct boundary | add isoform ambiguity flag | construct/readiness tests |
| Human-mouse orthology lookup | symbol/Ensembl ID | Ensembl REST | fixture yes | optional | no ortholog, ambiguous mapping, query error | mouse-model transferability required and no orthology evidence | write missing/error | live-Ensembl tests |
| ECD sequence extraction | human and mouse sequence/alignment | UniProt/Ensembl evidence | fixture yes | optional | empty ECD sequence | ECD identity requested and sequence absent | write missing/error | live-ECD fixture |
| Pairwise ECD identity | extracted ECD sequences | none | yes | no | missing sequence | identity gate requested and identity unavailable | write missing | live-ECD fixture |
| Normal-tissue risk | candidate table | HPA/GTEx future adapters | fixture yes | optional HPA only | source record missing or adapter not implemented | high-risk modality without tissue evidence | mark unknown/missing | HPA fixture test |
| Drug/biologic evidence | candidate table | Open Targets/ChEMBL future adapters | yes as missing | pending | adapter not implemented | user requests completed drug evidence | mark `adapter_not_implemented` | coverage diagnostics |
| Modality-specific decision | screening/readiness/risk rows | none | yes | no | insufficient modality evidence | gate fail | recommend fallback or not recommended | strategy tests |
| Construct design | screening table | none | yes | no | no ECD or unsuitable topology | intracellular-only or no extracellular region | cell-display fallback or no construct | construct tests |
| Report generation | tables above | none | yes | no | missing optional inputs | required screening table absent | produce partial report with gaps | smoke tests |

## Current Limitations

- HPA normal-tissue support is fixture-backed and adapter-ready, not complete production-scale live safety validation.
- Open Targets, ChEMBL, GTEx, ClinicalTrials, and MGI adapters are not implemented in this public release.
- Live UniProt/Ensembl checks are optional and are not required by CI.
- The public repository contains no private source data or unpublished output tables.
