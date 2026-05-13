# T4f Feedback Stabilization Design

## Objective

Stabilize the selected-confinement-only triaxial gate with full
`PorePressureFeedbackScale=1` before reintroducing axial loading. The source
change is intentionally narrow: it only modifies the acceleration that is added
by `PorePressureFeedback`.

## Options Considered

| Option | Description | T4f Decision |
| --- | --- | --- |
| Feedback relaxation | Use a first-order memory: `a_used = a_old + alpha (a_raw - a_old)`. | Implemented as opt-in. |
| Absolute acceleration cap | Limit `|a_fb|` to a user value. | Implemented as opt-in. |
| Ratio cap | Limit `|a_fb|` relative to the larger of current non-feedback acceleration and confining acceleration reference. | Implemented as opt-in. |
| Feedback timing/scale only | Existing T4e start/ramp/scale controls. | Retained, but T4e showed this is insufficient alone. |
| Operator smoothing | Smooth pressure/gradient before feedback. | Deferred because it risks changing operator interpretation more broadly. |

## Added Parameters

Defaults preserve old behavior.

| Parameter | Default | Meaning |
| --- | ---: | --- |
| `SavePorePressureFeedbackDiagnostics` | `0` | Print CPU feedback acceleration diagnostics. |
| `PorePressureFeedbackDiagInterval` | `1` | Print interval in steps when diagnostics are enabled. |
| `PorePressureFeedbackRelaxation` | `0` | `0` disables relaxation; `(0,1)` applies first-order relaxation. |
| `PorePressureFeedbackLimiterMode` | `0` | `0` none, `1` absolute cap, `2` ratio cap, `3` absolute plus ratio cap. |
| `PorePressureFeedbackMaxAccel` | `0` | Absolute acceleration cap in `m/s2`; disabled when `<=0`. |
| `PorePressureFeedbackMaxAccelRatio` | `0` | Ratio cap against non-feedback/confining acceleration; disabled when `<=0`. |

The existing T4e controls remain:

- `PorePressureFeedbackStartTime`;
- `PorePressureFeedbackRampEndTime`;
- `PorePressureFeedbackScale`.

## Numerical Form

For each material particle:

```text
a_raw = feedback_factor * a_operator
a_relaxed = a_old + alpha (a_raw - a_old)       if relaxation is enabled
a_used = cap(a_relaxed or a_raw)                if a cap is enabled
Ace += a_used
```

The previous used acceleration is stored in a CPU array and follows particle
sorting/periodic duplication. When the feedback gate factor is zero, this
stored acceleration is reset to zero so delayed feedback starts from rest.

## Diagnostics

The CPU log reports:

- feedback factor;
- applied particle count;
- raw and used acceleration max/mean;
- non-feedback acceleration max;
- used/reference ratio max;
- confining acceleration reference;
- limiter and relaxation activation counts;
- class-wise lateral/cap/interior used feedback acceleration maxima.

## GPU Status

Non-default feedback timing or stabilization remains CPU-only. GPU builds pass,
but GPU simulation hard-errors when T4e/T4f feedback controls are enabled.
