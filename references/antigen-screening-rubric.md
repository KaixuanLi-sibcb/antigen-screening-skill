# Antigen Screening Rubric

## Required Gates

Gate calls must be reported independently:

1. antigen accessibility
2. disease relevance
3. normal tissue risk
4. mouse-model transferability
5. constructability

## Scoring Policy

Use tie-break scores only after gate calls. A score cannot override:

- intracellular or nuclear localization for surface targeting
- missing topology for a definitive surface-antigen claim
- high normal-tissue risk for a modality where the risk is unacceptable
- unavailable ECD for a construct-design claim

When locally supplied identity fields are present, `ECD_identity` is the only local identity field allowed for cross-species interpretation. Whole-protein `seq_identity` may be retained for audit but cannot drive that gate.

Do not conflate two different uses of `ECD_identity`:

- Mouse-model transferability: higher human-mouse ECD identity is favorable.
- Antibody-screening report priority: lower human-mouse ECD identity can be favorable when the objective is divergent human ECD antigenicity.

## Default Tie-Break Components

| Component | Direction |
|---|---|
| confirmed surface accessibility | positive |
| clean continuous ECD | positive |
| disease relevance evidence | positive |
| high-risk normal expression | negative |
| ECD identity above threshold | positive for mouse-model transferability |
| ECD identity below threshold | positive only when the explicit report objective is low-identity antibody screening |
| approved or clinical evidence | context-dependent, not automatically positive |

## Decision Language

Use `go`, `conditional`, `no_go`, or `control_or_not_applicable`. Include one short rationale and missing evidence.
