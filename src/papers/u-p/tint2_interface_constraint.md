# TINT2 Interface Constraint

Date: 2026-05-14

TINT2 must test pore-pressure time staging without adding another open-ended
mode family. The purpose is to determine whether the current pressure update
placement contributes to L5/BND1 feedback instability, not to create a new
permanent configuration surface.

## Allowed Interface

Only this selector is allowed by default:

```text
PorePressureTimeIntegrationMode
  0 = current behavior, default
  1 = CPU end-step pressure commit
  2 = reserved; do not implement additional behavior in TINT2
```

Rules:

- mode `0` must preserve current behavior;
- mode `1` must be CPU-first;
- GPU must hard-error for nonzero mode unless explicitly implemented later;
- mode `2` is only a placeholder to prevent immediate mode creep;
- no mode `3/4` may be added in TINT2.

## Diagnostics Constraint

Avoid adding diagnostics XML parameters unless absolutely necessary.

Preferred alternatives:

- reuse `PorePress`, `ExcessPorePress`, `PorePressRate`, `DivVel`,
  `LapPorePress`, `LapZ`, and feedback acceleration output;
- add one-time log summaries;
- compute `DeltaP_rate`, `DeltaP_actual`, and boundary residuals in
  postprocessing when possible.

If source-level pressure-stage diagnostics are required, the only acceptable
new switch is:

```text
SavePorePressureTimeStageDiagnostics
```

It must be documented as:

```text
[ACTIVE_EXPERIMENTAL] [DELETE_CANDIDATE] [CPU_ONLY] [GPU_HARD_ERROR]
```

and must have a TINT2-clean decision immediately after the test matrix.

## Required TINT2-Clean Decision

After TINT2, write a decision note before any BND2, GPU port, or landslide
baseline:

- If mode `1` improves or clarifies L3c/L5/BND1 behavior, keep it as
  `[ACTIVE_EXPERIMENTAL]` and plan TINT3 promotion/cleanup.
- If mode `1` is neutral, deprecate it unless it makes the time-stage semantics
  significantly clearer.
- If mode `1` worsens the gates, delete or mark it `[DELETE_CANDIDATE]`.
- Do not port nonzero modes to GPU until mode `1` has a positive CPU decision.

## Required TINT2 Test Matrix

Minimum CPU Release matrix:

1. L3c feedback-off, operator `1`, mode `0` versus mode `1`.
2. L5 feedback-on, operator `1`, mode `0` versus mode `1`.
3. BND1 generalized operator `2`, feedback-off, mode `0` versus mode `1`.
4. BND1 generalized operator `2`, feedback-on short, mode `0` versus mode `1`.

Pass criteria:

- default mode `0` is unchanged;
- mode `1` does not worsen L3c analytical/boundary metrics;
- mode `1` improves or at least clarifies L5 feedback metrics;
- mode `1` reduces BND1 mode `2` feedback-on instability if stage mismatch is
  a real contributor;
- top drained and bottom no-flux projections remain clean.

## What TINT2 Must Not Do

- Do not change the PR governing equation.
- Do not change boundary mode logic.
- Do not change `PorePressureFeedback` formulation.
- Do not change the default.
- Do not add a diagnostics-mode family.
- Do not port GPU before CPU mode `1` passes.
