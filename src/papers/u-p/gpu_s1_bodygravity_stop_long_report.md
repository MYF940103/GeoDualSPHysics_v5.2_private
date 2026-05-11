# GPU S1 BodyGravityStopTime long run

## Objective

This stage runs the Scenario 1 single-run `BodyGravityStopTime` route to `TimeMax=3.6 s` on GPU Release. It checks whether the post-switch dissipation stage remains stable after the S1-1b GPU gravity-stop patch and S1-2 medium smoke.

## S1-1b Short Parity Recap

S1-1b added GPU `BodyGravityStopTime` support. The GPU mechanical body gravity stopped at about `t=0.00200051 s`, `HydraulicGravity` remained active, and the final short-window CPU/GPU differences were about `0.00394 Pa` for `PorePress`/`ExcessPorePress` and `6e-09 m/s` for velocity.

## S1-2 Medium Recap

S1-2 passed GPU medium windows:

- `0.05 s`: `code=0`, `excluded=0`, final `ExcessPorePress` maxAbs `84.08 Pa`.
- `0.2 s`: `code=0`, `excluded=0`, final `ExcessPorePress` maxAbs `27.36 Pa`.

No CPU medium/long reference was run because CPU cost was high; S1-1b remains the CPU/GPU parity anchor.

## Long-Run Setup

- `PorePressureBoundaryOperator=0`
- `BodyGravityStopTime=0.002`
- `PorePressureTopDrained=1`
- `PorePressureTopDrainedStartTime=0.002`
- `PorePressureBottomNoFlux=1`
- `Gravity=(0,0,-9.81)`
- `HydraulicGravity=(0,0,-9.81)`
- `HydromechDampingXi=0.05`
- `PorePressureFeedback=1`, mode `1`, operator `1`
- `PorePressureShepard=1`, interval `10`, mode `1`
- `PorePressureDtSafety=0.20`
- `SavePorePressure=1`
- GPU Release, `TimeMax=3.6`, `TimeOut=0.1`

## Runtime / Steps / Frames

| code | excluded | steps | runtime_s | frames | final_time | gravity stop log | hydraulic gravity active log |
|---:|---:|---:|---:|---:|---:|---|---|
| 0 | 0 | 3775438 | 8841.972656 | 37 | 3.6 | True | True |

## Final State

| metric | value |
|---|---:|
| final max velocity [m/s] | 2.99721e-07 |
| final mean velocity [m/s] | 1.91873e-07 |
| final mean settlement [m] | -1.89342e-07 |
| final PorePress max [Pa] | 9759.3 |
| final PorePress mean [Pa] | 4903.96 |
| final ExcessPorePress maxAbs [Pa] | 1.64504 |
| final ExcessPorePress mean [Pa] | -1.04579 |
| final bottom excess mean [Pa] | -1.64484 |
| final top layer excess maxAbs [Pa] | 1.40389e-09 |
| final bottom no-flux proxy [Pa] | 1.86976e-06 |
| final PorePressRate maxAbs [Pa/s] | 15582.4 |
| final DivVel contribution maxAbs [Pa/s] | 613.143 |
| final hydraulic contribution maxAbs [Pa/s] | 15581.8 |
| final PorePressureAccelDiff maxAbs [m/s2] | 0.00128495 |
| excess envelope peak [Pa] | 38.5451 |
| excess envelope final / peak | 0.0426782 |
| velocity final / peak | 0.0249468 |

## Gravity Stop Verification

The GPU long run detected the same one-time gravity-stop log used in S1-1b/S1-2:

- `Mechanical body gravity stopped on GPU ...`
- `Hydraulic gravity remains active.`

This confirms the long run used the Scenario 1 single-run route rather than the Scenario 2 always-on body-gravity route.

## Medium Overlap

The long run frame nearest `t=0.2 s` was `t=0.2 s`.

| quantity | S1-2 medium 0.2 s final | S1-3 long near 0.2 s |
|---|---:|---:|
| ExcessPorePress maxAbs [Pa] | 27.3597 | 27.3566 |
| bottom excess mean [Pa] | -27.3506 | -27.3475 |
| max velocity [m/s] | 5.59964e-06 | 5.59949e-06 |

The overlapping values are expected to be close because the XML settings are the same apart from the longer `TimeMax` and coarser long-run output interval.

## Boundary Checks

- Top-drained excess remained near zero after activation.
- The bottom no-flux proxy stayed small and finite over the long run.
- No pressure blow-up or switch-induced velocity spike was observed.

## Recommendation

Scenario 1 `BodyGravityStopTime` single-run GPU route is validated for the long-run stability gate if `code=0`, `excluded=0`, and the final residuals above are accepted. The next step is S1-4 paper-figure/reference comparison. The restart route remains deferred.

## Artifacts

- XML/BAT, analysis script, CSV files, and figures: `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_S1_BodyGravityStopLong/`
