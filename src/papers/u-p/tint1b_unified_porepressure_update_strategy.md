# TINT1b Unified Pore-Pressure Update Strategy

Date: 2026-05-14

## Strategy 0: Current Mode

Keep current behavior as default:

```text
Interaction_Forces computes rate and feedback
UpdatePorePressure runs before mechanical update/corrector
Shepard and clamps run in current locations
```

This is the regression baseline and should remain `PorePressureTimeIntegrationMode=0`.

## Strategy 1: End-Step Update

Goal: make the operator split explicit and stage-consistent.

Proposed chain:

1. `Interaction_Forces` computes `DivVel`, `LapPorePress`, `LapZ`, boundary
   operator contributions, feedback acceleration, and `PorePressRate` using
   previous-step pressure.
2. Feedback acceleration intentionally uses previous-step pressure.
3. Mechanical Verlet update or Symplectic corrector completes.
4. `UpdatePorePressure` runs at the end of the step.
5. Shepard runs immediately after the moved update.
6. Top drained, bottom no-flux, and any active clamp/projection run immediately
   after Shepard.
7. Output sees corrected end-step pressure.

This is still first-order split, but it avoids committing `PorePress^{n+1}`
before the same mechanical corrector.

## Strategy 2: Rate-and-Correction Bookkeeping

Add diagnostics for pressure changes:

```text
P_old
DeltaP_rate = PorePressRate * dt
P_raw = P_old + DeltaP_rate
DeltaP_shepard
DeltaP_top_clamp
DeltaP_bottom_projection
DeltaP_boundary_projection
P_new
DeltaP_actual = P_new - P_old
DeltaP_correction = DeltaP_actual - DeltaP_rate
```

These diagnostics should be optional:

```text
SavePorePressureTimeStageDiagnostics=0/1
```

Minimum useful summaries:

- min/max/mean `DeltaP_rate`;
- min/max/mean `DeltaP_actual`;
- max absolute correction;
- affected count for each correction type;
- update stage label;
- `dt` and `dt_pore`.

## Strategy 3: Future Predictor-Corrector

Longer-term route:

- allocate pressure predictor arrays;
- compute pressure half-step;
- recompute rate at predicted state;
- correct pressure at full step;
- define whether feedback uses old, half-step, or corrected pressure.

This is not recommended as the first source patch because it requires a second
hydraulic operator pass and a GPU design.

## TINT2 Minimum Recommendation

Implement:

```text
PorePressureTimeIntegrationMode=0/1
SavePorePressureTimeStageDiagnostics=0/1
```

Semantics:

- mode `0`: current behavior;
- mode `1`: CPU-only end-step update;
- GPU hard error for nonzero mode;
- no PR governing-equation changes;
- no boundary-operator default changes.

TINT2 should move the pressure update and all post-pressure corrections as one
unit, not just move `UpdatePorePressure()` alone.

## Verification Priority

1. L3c feedback-off, operator `1`: must not worsen analytical metrics.
2. L5 feedback-on, operator `1`: must remain stable.
3. BND1 generalized mode `2` feedback-off: must remain stable.
4. BND1 generalized mode `2` feedback-on short gate: should reduce exclusions,
   `DtMin` bursts, pressure peaks, or at least clarify failure mechanism.

Landslide should remain deferred until this matrix is understood.

