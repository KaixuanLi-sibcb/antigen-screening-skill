# Architecture

The antigen-screening skill is organized as an evidence-driven workflow framework. It separates reusable scientific guidance, schema contracts, command-line entrypoints, and importable Python modules so the workflow can be validated from a clean checkout without private data.

## Framework Layers

1. Skill router: `SKILL.md` defines trigger conditions, hard rules, stop conditions, and minimum outputs.
2. Static guidance: `static/` and `references/` define gate logic, evidence semantics, construct rules, and reporting formats.
3. Schemas: `schemas/` defines candidate inputs, output columns, coverage diagnostics, report-priority outputs, and EvidenceRecord v2 shape.
4. CLI entrypoints: `scripts/*.py` expose validation, fixture smoke tests, generic scoring, live-ECD validation, and planning modules.
5. Package modules: `scripts/antigen_screening/` contains parsers, topology interpretation, ECD extraction, evidence provenance, scoring, readiness, normal-tissue, screening-strategy, validation-ladder, and reporting logic.
6. Tests and fixtures: `tests/` provides privacy-safe regression coverage for the workflow without relying on private source files or live network access.

## Data Flow

```text
candidate TSV, omics-derived candidates, or manual target lists
  -> schema normalization
  -> evidence provenance capture
  -> antigen accessibility gates
  -> topology, ECD, and constructability review
  -> cross-species ECD conservation review
  -> normal-tissue risk annotation
  -> antigen readiness and screening-material planning
  -> validation-ladder planning
  -> TSV, JSONL, and Markdown outputs
```

## Gate Policy

The workflow is gate-first. Tie-break scores are used only after gate outcomes are visible and cannot override accessibility, normal-tissue, mouse-transferability, modality, or constructability failures.

## Provenance Policy

EvidenceRecord v2 is the shared contract across fixture evidence, local tabular evidence, live public sources, computed values, missing evidence, and conflict rows. Adapters must write explicit `missing` or `error` records when evidence cannot be obtained.

## Privacy Boundary

The repository is intentionally self-contained for fixture validation. Private source files and generated output folders are not part of the Git history, package artifact, or CI workflow.
