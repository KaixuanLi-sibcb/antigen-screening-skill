# Changelog

## Public release preparation

- Created a sanitized public workflow release from a no-history snapshot.
- Removed private-data importer entrypoints, private regression docs, generated-output logs, and source-data references from the public tree.
- Renamed the public package and skill to `antigen-screening`.
- Kept fixture-based validation, EvidenceRecord v2 provenance, live-ECD fixture validation, coverage diagnostics, antigen readiness, HPA fixture risk, screening strategy, validation ladder, and report-priority generation.
- Updated privacy checks so tracked spreadsheets, local data, generated output folders, package artifacts, and caches cannot be committed.

## v0.4.0

- Added report-priority ranking with explicit ECD identity preference modes.
- Added coverage diagnostics and ID rescue for missing-evidence interpretation.
- Added antigen readiness, normal-tissue risk fixture adapter, screening strategy, and antibody validation ladder.
- Added UniProt/Ensembl fixture-backed live-ECD validation.
- Added EvidenceRecord v2 provenance and conflict reporting.
