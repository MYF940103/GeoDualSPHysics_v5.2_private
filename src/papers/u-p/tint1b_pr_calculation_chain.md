# TINT1b PR Calculation Chain

Date: 2026-05-14

## Current CPU Verlet Chain

1. `Interaction_Forces(INTERSTEP_Verlet)` runs mechanical SPH interactions.
2. `ComputeHydroDivVel()` accumulates `DivVel` from current `Posc` and
   `Velrhopc`.
3. `ComputeHydroLapPorePress()` accumulates material-material `LapPorePress`
   from current `PorePress`.
4. `ComputeHydroLapZ()` accumulates material-material elevation Laplacian.
5. `ApplyPorePressureBoundaryOperator()` adds mode `1/2/3` boundary
   contributions to `LapPorePress` and `LapZ`, still using current old/stage
   pressure.
6. Feedback acceleration candidates are computed from current old/stage
   pressure.
7. `ApplyPorePressureFeedback()` adds feedback acceleration to `Acec`.
8. `ComputeHydroPorePressRatePR()` computes:

   ```text
   PorePressRate = (K_w/n) * (-DivVel + k/(rho_w g) LapPorePress + k LapZ)
   ```

9. `DtVariable(true)` selects the step dt.
10. `UpdatePorePressure()` commits `PorePress += PorePressRate * dt`.
11. Optional Shepard regularization overwrites pressure.
12. Motion/shifting and `ComputeVerlet()` update position, velocity, density,
    and stress.
13. Post-update top drained and bottom no-flux material clamps overwrite
    pressure.
14. Output later writes corrected `PorePress` but last interaction-stage
    `PorePressRate`.

Pressure used by rate: old/stage pressure.

Pressure used by feedback: old/stage pressure.

Pressure output: post-correction persistent pressure.

## Current CPU Symplectic Chain

1. Predictor interaction computes mechanical acceleration from current state.
2. `ComputeSymplecticPre()` advances position, velocity, density, and stress
   to predicted half-step arrays.
3. Cell division is rebuilt on predicted state.
4. Corrector interaction computes `DivVel`, `LapPorePress`, `LapZ`, boundary
   contributions, feedback acceleration, and `PorePressRate`.
5. `PorePressRate` uses predicted mechanical variables but old pressure because
   there is no pressure predictor.
6. `UpdatePorePressure()` commits the scalar pressure update.
7. Optional Shepard regularization overwrites pressure.
8. `ComputeSymplecticCorr()` completes the mechanical corrector using feedback
   acceleration already computed from old pressure.
9. Post-update top drained and bottom no-flux material clamps overwrite
   pressure.
10. Output later writes corrected pressure and last corrector-stage rate.

Pressure used by rate: old pressure on predicted mechanical geometry.

Pressure used by feedback: old pressure on predicted mechanical geometry.

Pressure output: post-correction persistent pressure.

## Current GPU Chain

GPU follows the same high-level chain:

- Verlet: interaction, `UpdatePorePressureGpu()`, optional Shepard/top/bottom,
  then `ComputeVerlet()`.
- Symplectic: predictor interaction, predictor mechanics, corrector
  interaction, `UpdatePorePressureGpu()`, optional Shepard/top/bottom, then
  `ComputeSymplecticCorr()`.

GPU support is narrower:

- feedback operator `1` only;
- boundary operator `1` only;
- generalized mode `2` remains CPU-only.

## Proposed End-Step Chain for TINT2

1. Interaction computes `DivVel`, `LapPorePress`, `LapZ`, feedback, and
   `PorePressRate` from previous-step pressure.
2. Feedback acceleration intentionally uses previous-step pressure.
3. Mechanical step/corrector completes first.
4. `UpdatePorePressure()` runs at end of step using the stored rate.
5. Shepard and top/bottom clamps run immediately after the scalar update.
6. Diagnostics record:

   ```text
   DeltaP_rate = PorePressRate * dt
   DeltaP_actual = P_new_corrected - P_old
   DeltaP_correction = DeltaP_actual - DeltaP_rate
   ```

7. Output uses corrected `PorePress` and stores the stage label.

Pressure used by rate: previous-step pressure.

Pressure used by feedback: previous-step pressure.

Pressure output: corrected end-step pressure.

Benefit: the split is explicit and avoids writing `PorePress^{n+1}` before the
same mechanical corrector uses feedback computed from `PorePress^n`.

## Future Predictor-Corrector Chain

1. Compute rate at state `n`.
2. Predict `PorePress^{n+1/2}`.
3. Run mechanical predictor with pressure-stage policy defined.
4. Recompute hydraulic operators using predicted pressure and predicted
   mechanical state.
5. Correct `PorePress^{n+1}`.
6. Apply final correction/clamp.

This requires at least one new pressure staging array and likely a second
hydraulic operator evaluation. It is not recommended as the first TINT2 patch.

