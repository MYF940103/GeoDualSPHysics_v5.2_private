# Cryer FlexibleConfinement Ramp/Drainage Cleanup and Next Steps

Date: 2026-06-20

## Cleanup

Removed old raw output directories from previous short/screening tests:

- `zhao_flex_full003/out`
- `zhao_flex_drained_ramp001/out`
- `sweep_ramp_drainage_20260620/r001_drainRamp/out`
- `sweep_ramp_drainage_20260620/r003_drain0/out`
- `sweep_ramp_drainage_20260620/r003_drainRamp/out`
- `sweep_ramp_drainage_20260620/r005_drain0/out`
- `sweep_ramp_drainage_20260620/r005_drainRamp/out`
- `sweep_ramp_drainage_20260620/r010_drain0/out`

Kept lightweight scripts, logs, CSV/JSON summaries, figures, and README notes.

Preserved the full validation output:

- `r010_drain0_full_20260620/out`

## Current Best Full Validation

Case:

- `r010_drain0_full_20260620`

Configuration:

- `HydroMechTopLoadMode = 3` (`FlexibleConfinement`)
- `HydroMechTopLoadRampTime = 0.01 s`
- `HydroMechDrainage = 1`
- `HydroMechDrainageStartTime = 0`
- `HydraulicConductivity = 1e-4 m/s`
- `SoilDampingCoef = 0.02`
- Analytical comparison uses `t_analytic = t - ramp_end`.

Full-cycle result:

- Peak center `p/q0 = 1.126` at `t = 0.010 s`
- Final center `p/q0 = 0.00291`
- Final analytical `p/q0 = 0.000423`
- RMSE = `0.04157`
- MAE = `0.02866`
- Max speed = `0.00717 m/s`
- Final max speed = `3.10e-5 m/s`

## Interpretation

The dominant remaining error is the initial post-ramp overshoot. Later-time dissipation is much closer to the analytical trend than earlier two-stage or short-ramp tests.

The ramp/drainage sweep showed:

- Opening drainage from the start is more stable than opening it suddenly after ramp completion.
- Increasing ramp from `0.001 s` to `0.010 s` reduced peak overshoot and max velocity.
- Delayed drainage cases had slightly lower short-window RMSE after ramp alignment, but their velocity spikes were much larger (`~0.039-0.040 m/s`), so they are not preferred.

## Recommended Next Tests

Prioritize ramp-time tuning with drainage active from `t=0`:

1. `RampTime = 0.015 s`, `DrainageStartTime = 0`
2. `RampTime = 0.020 s`, `DrainageStartTime = 0`

Use short early-window runs first. If one reduces the peak below `~1.10 q0` without increasing late-time error or max velocity, run a full cycle.

Damping should be a secondary sweep:

- Do not increase damping aggressively first, because high damping can artificially freeze oscillations and hide stress redistribution.
- If ramp tuning plateaus, test `SoilDampingCoef = 0.01, 0.02, 0.05` using the best ramp time.
