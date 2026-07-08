# Report Priority Ranking

The report-priority layer creates a presentation-ready ranking from existing screening outputs. It is a reporting layer, not a replacement for gate-level evidence.

## Identity Direction

Human-mouse ECD identity has two different interpretations:

- `high_for_mouse_model_transferability`: high ECD identity supports mouse-model transferability and potential cross-species binding.
- `low_for_antibody_screening`: low ECD identity supports antibody-screening priority when the goal is to favor divergent human ECD antigenicity over mouse.

The default report mode is `low_for_antibody_screening`.

This means `mouse_model_transferability_gate=fail` is retained as an audit column, but it is not treated as a report-level no-go in the antibody-screening ranking. A low human-mouse ECD identity can be a positive ranking feature for antibody screening.

## Outputs

`scripts/export_ranked_report.py` writes:

- `report_priority_table.tsv`
- `report_priority_summary.json`
- `report_priority_report.md`
- `report_priority_workbook.xlsx`

The workbook includes summary, all ranked candidates, top candidates, A/B/C/D bucket sheets, and the selected identity-preference mode.

## Limits

The report-priority layer does not run HPA/GTEx, Open Targets, ChEMBL, ClinicalTrials, or live ECD adapters. Missing evidence remains missing and is not converted into negative evidence.
