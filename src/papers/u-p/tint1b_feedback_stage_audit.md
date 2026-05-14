# TINT1b Feedback Stage Audit

Date: 2026-05-14

## Current Feedback Placement

Pore-pressure feedback is computed inside `Interaction_Forces()` after the PR
diagnostic operators and before `ComputeHydroPorePressRatePR()`.

CPU sequence:

1. `ComputeHydroDivVel()`;
2. `ComputeHydroLapPorePress()`;
3. `ComputeHydroLapZ()`;
4. optional boundary operator contribution;
5. `ComputePorePressureAccel*()`;
6. `ApplyPorePressureFeedback()`;
7. `ComputeHydroPorePressRatePR()`.

`ComputePorePressureAccel*()` reads the pressure field that exists during
interaction. It does not see the pressure that will be produced later by
`UpdatePorePressure()`.

## Pressure Time Layer Used by Feedback

Current feedback pressure:

- Verlet: pressure from the beginning of the step.
- Symplectic corrector: pressure from the beginning of the full step, evaluated
  on predicted mechanical positions/densities.

The updated scalar pressure affects feedback only at the next interaction.

## Same-Step Closed Loop

There is no direct same-step closed loop:

```text
p_new does not feed Ace_feedback in the same step.
```

There is an indirect loop across steps:

```text
p_old -> feedback acceleration -> mechanics -> DivVel -> PorePressRate -> p_new
```

This is an explicit lagged coupling. It is acceptable if intentional and
stable, but it should be documented and diagnosed.

## Proposed Mode 1 Interpretation

For TINT2 Strategy 1, feedback should intentionally use previous-step pressure.
That makes the split explicit:

```text
mechanics stage uses p^n
pressure update commits p^{n+1} at end of step
next mechanics stage uses p^{n+1}
```

This is not second-order coupled, but it is clearer than updating pressure
before the same mechanical corrector while still using feedback from old
pressure.

## Diagnostics Time Layer

Feedback diagnostics currently record raw and used acceleration from the
interaction-stage pressure. TINT2 should label this explicitly as:

```text
feedback_pressure_stage = previous_step_or_stage
```

If `PorePressureTimeIntegrationMode=1` is added, feedback diagnostics should
continue to describe the old-pressure mechanical solve, while pressure
DeltaP diagnostics describe the end-step hydraulic solve.

## Relation to L5 and BND1

L5 operator `1` remains stable, so the current lagged feedback is not
automatically invalid.

BND1 mode `2` feedback-on failure is plausibly amplified by staging:

- mode `2` adds stronger ordinary-wall boundary Laplacian terms;
- feedback uses old pressure but mechanics may generate new divergence;
- updated pressure is committed before the same mechanical corrector;
- post-update pressure corrections are not represented in `PorePressRate`;
- feedback-on then sees the corrected pressure one step later.

This supports a TINT2 split-mode experiment before more boundary tuning.

