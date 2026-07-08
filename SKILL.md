---
name: antigen-screening
description: Use this skill for antigen screening, surface target prioritization, ECD construct planning, antibody/CAR/ADC target evaluation, or human-mouse ECD conservation checks from gene lists, omics candidates, or manual target lists. Do not use for general pathway analysis or intracellular-only biomarker ranking.
---

# Antigen Screening

## When To Use

Use this skill when a user provides candidate genes, candidate proteins, scRNA markers, bulk RNA-seq DEGs, proteomics surfaceome hits, or manual antigen targets and asks for surface-antigen triage, ECD construct planning, modality suitability, normal-tissue risk annotation, coverage diagnostics, or antibody-screening strategy.

## When Not To Use

Do not use this skill for general pathway enrichment, intracellular biomarker ranking, mutation neoantigen prediction, or final biological validation claims.

## Required Inputs

Minimum input is a candidate TSV with `gene_symbol`, `species`, `modality`, `disease_context`, and `user_evidence`. Optional evidence can include UniProt accession, Ensembl ID, ECD identity, topology, normal-tissue risk rows, or EvidenceRecord v2 JSONL.

## Minimum Viable Output

Every run should produce machine-readable TSV or JSON plus a human-readable Markdown report. For smoke tests, generate `antigen_screening_table.tsv`, `evidence_records.jsonl`, `risk_flags.tsv`, `construct_plan.tsv`, and `report.md`.

## Hard Rules

- Do not call a target a surface antigen from gene symbol alone.
- Do not treat RNA expression as surface protein evidence.
- Do not substitute whole-protein identity for ECD identity.
- Do not treat drug or antibody evidence as automatically positive; it may indicate safety risk, competition, or known toxicity.
- Do not propose ECD constructs for intracellular or nuclear proteins.
- If UniProt topology is missing, mark topology evidence as inferred or missing.
- If isoforms can change ECD or transmembrane topology, mark isoform ambiguity.
- If network access is unavailable, use only fixture or local evidence and state that live sources were not checked.
- Distinguish `confirmed`, `inferred`, `missing`, and `not_applicable` claims.
- Missing evidence is not negative evidence.
- Generated outputs must be TSV/JSON plus human-readable Markdown.
- Do not commit raw spreadsheets, private source data, generated outputs, cache, or package artifacts.

## Evidence Model

Use EvidenceRecord v2 for provenance. Record source name, authority level, version, query, retrieval time when available, raw-response hash when available, evidence status, conflict status, failure mode, and license note. Use explicit `missing`, `not_applicable`, `conflict`, or `error` records instead of dropping absent evidence.

## Decision Gates

1. Antigen accessibility: pass, fail, or uncertain.
2. Disease relevance: pass, fail, or uncertain.
3. Normal-tissue risk: low, medium, high, or unknown.
4. Mouse-model transferability or antibody-screening specificity: use ECD identity only and make the ranking direction explicit.
5. Constructability: pass, partial, fail, or not applicable.

Scores are tie-breakers only and must not override gate failures.

## Output Artifacts

Typical artifacts include screening table, construct plan, evidence JSONL, conflict report, coverage diagnostics, antigen-readiness table, normal-tissue risk table, screening-strategy plan, validation ladder, and report-priority table.

## Tool And Script Usage Policy

Prefer the scripts in `scripts/` for repeatable work. Use fixture mode for CI and offline checks. Use live UniProt/Ensembl/HPA only when explicitly requested or when network access is acceptable. Never imply a database was checked if the adapter was not run or failed.

## Stop Conditions

Stop and report when required inputs are missing, evidence mapping is ambiguous without a safe rescue, topology contradicts the requested modality, private data would need to be committed, or a live adapter fails in a way that prevents the requested validation.
