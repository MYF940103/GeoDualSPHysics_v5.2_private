# A2 Initial-State Calibration Audit for Self-Weight Scenario 2

Date: 2026-05-12

## Objective

A1 showed that the remaining GPU Scenario 2 bottom-excess discrepancy is not
primarily explained by the legacy boundary layer correction: GPU
`PorePressureBoundaryOperator=0` and `1` gave essentially identical long-run
errors. A1 also showed that a modest effective consolidation-coefficient scale
(`cv x 1.12`) reduced the bottom-excess relative RMSE from about 7.6% to about
2.0%.

This A2 audit checks the other major suspicion: the analytical comparison
assumes that at the drainage activation time (`t=0.002 s`) the solver has
already generated the Supporting Materials Eq. (4) undrained self-weight excess
profile. The previous long-run outputs did not save that early state. A2
therefore performs one targeted short GPU Release run and compares the retained
early profiles against Eq. (4).

No source code was modified. No CPU/GPU long-run reproduction was executed.

## Output Directory

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/Analytical_Audit_A2_InitialState/
```

Retained files:

- `CaseSW_S2_GPU_A2_InitAudit_Def.xml`
- `xCaseSW_S2_GPU_A2_InitAudit_win64_GPU_release.bat`
- `analyze_a2_initial_state.py`
- `a2_frame_metrics.csv`
- `generated_initial_profile_metrics.csv`
- `initial_state_comparison.csv`
- `measured_reference_metrics.csv`
- `cv_fit_metrics.csv`
- `cv_fit_sensitivity.csv`
- `effective_cv_summary.csv`
- `fd_reference_metrics.csv`
- `fd_reference_bottom_timeseries.csv`
- `analytical_vs_measured_reference_bottom_timeseries.csv`
- `analytical_vs_measured_reference_profiles.csv`
- `figures/*.svg`
- `figures/*.png`

Generated DualSPHysics output was removed after the analysis.

## Targeted Short-Run Setup

The short run is based on the G9b `xi=0.05`, mode-0 setup:

- `PorePressureBoundaryOperator=0`
- `HydromechDampingXi=0.05`
- `PorePressureTopDrainedStartTime=0.002 s`
- `PorePressureBottomNoFlux=1`
- `PorePressureShepard=1`
- `PorePressureShepardInterval=10`
- `PorePressureShepardMode=1`
- `PorePressureFeedback=1`
- `PorePressureFeedbackMode=1`
- `PorePressureFeedbackOperator=1`
- `PorePressureDtSafety=0.20`
- `SavePorePressure=1`
- `TimeMax=0.05 s`
- `TimeOut=0.001 s`

The GPU Release targeted run completed with:

| Quantity | Value |
|---|---:|
| code | 0 |
| excluded | 0 |
| retained frames | 51 |
| material particles | 1000 |
| final retained time | 0.050 s |

## Eq. (4) vs Generated Early Profiles

The closest retained frame to drainage activation is `frame=2`, `t=0.002 s`.
At this time the generated excess-pressure profile is not Eq. (4):

| Time (s) | Profile relative RMSE vs Eq. (4) | Bottom excess (Pa) | Eq. (4) bottom (Pa) | Bottom ratio |
|---:|---:|---:|---:|---:|
| 0.000 | 1.00000 | 0.00 | 20312.96 | 0.0000 |
| 0.001 | 0.92243 | 2687.71 | 20312.96 | 0.1323 |
| 0.002 | 0.41399 | 13601.78 | 20312.96 | 0.6696 |
| 0.003 | 0.42532 | 27526.45 | 20312.96 | 1.3551 |
| 0.005 | 0.68530 | 30174.16 | 20312.96 | 1.4855 |
| 0.010 | 0.10383 | 20446.89 | 20312.96 | 1.0066 |
| 0.020 | 0.03946 | 18825.56 | 20312.96 | 0.9268 |
| 0.050 | 0.07532 | 17013.02 | 20312.96 | 0.8375 |

The key point is not merely that there is an initial-state mismatch. The early
coupled response is dynamic: the bottom excess undershoots Eq. (4) at
`t=0.002 s`, overshoots it at `t=0.003-0.005 s`, and becomes closest to the
Eq. (4) shape around `t=0.01-0.02 s`. Therefore there is no single saved
`t=0.002 s` solver frame that can cleanly replace Eq. (4) as a quasi-static
analytical initial condition.

## Measured-Initial Reference Reconstruction

Several 1D reference variants were propagated using the same top-drained /
bottom-no-flux eigenbasis used in A1. For bottom excess against the existing
GPU G9b `mode=0`, `xi=0.05` long run:

| Reference | RMSE (Pa) | Relative RMSE |
|---|---:|---:|
| Eq. (4) + nominal `cv` | 550.17 | 0.07594 |
| Eq. (4) + nominal `cv`, bottom-layer mean | 549.18 | 0.07581 |
| measured `t=0.002` + nominal `cv` | 2440.77 | 0.56586 |
| measured `t=0.010` + nominal `cv` | 1282.31 | 0.16024 |
| measured `t=0.020` + nominal `cv` | 768.69 | 0.10284 |
| Eq. (4) + best-fit `cv` | 135.56 | 0.01984 |
| measured `t=0.010` + best-fit `cv` | 577.60 | 0.08117 |

The measured-initial variants do not improve the long-run analytical
comparison. The Eq. (4) initial condition remains the best nominal initial
profile among the tested options. This means the 8% discrepancy is not fixed by
replacing Eq. (4) with the raw generated `t=0.002 s` profile.

## Effective cv Calibration

The Eq. (4)-based best-fit `cv` scale is:

| Fit window (s) | Best `cv` scale | Relative RMSE |
|---:|---:|---:|
| 0.002-0.5 | 1.1975 | 0.01097 |
| 0.01-1.0 | 1.1550 | 0.01324 |
| 0.002-3.6 | 1.1175 | 0.01984 |

The scale is not perfectly constant: earlier windows prefer a slightly larger
effective `cv`, while the full retained window gives the A1-like value near
`1.12`. This is consistent with a dynamic storage / time-factor mismatch rather
than a boundary-condition-only error.

## Finite-Volume Reference Check

A standalone implicit 1D finite-volume solver was also run for Eq. (4) and for
the measured `t=0.010 s` profile. The finite-volume solution and the series
projection agree to within a few pascals:

| Reference | Comparison | RMSE (Pa) | Relative RMSE |
|---|---|---:|---:|
| Eq. (4) | GPU vs FD | 554.22 | 0.07645 |
| Eq. (4) | FD vs series | 4.20 | 0.00058 |
| measured `t=0.010` | GPU vs FD | 1286.43 | 0.16068 |
| measured `t=0.010` | FD vs series | 4.30 | 0.00054 |

Thus the reconstruction method itself is not the source of the discrepancy.

## Bottom-Layer Averaging

Changing the reference from a bottom point value to a bottom-layer mean changes
the Eq. (4) nominal relative RMSE only from `0.07594` to `0.07581`. This is a
real convention difference, but it is too small to explain the observed
discrepancy.

## Updated Error Attribution

After A2, the likely error-source ranking is:

1. Effective `cv` / dynamic storage / time-factor mapping.
2. Early dynamic self-weight generation before the quasi-static Eq. (4) state
   is reached.
3. SPH discretization, Shepard smoothing, and coupled mechanics details.
4. Bottom-layer extraction convention.
5. Hydraulic boundary layer correction. B5 already showed mode 0 and mode 1
   are nearly identical in long-run bottom excess.

## Answers to the A2 Questions

1. The actual generated excess profile at `t≈0.002 s` is not Eq. (4). Its bottom
   excess is only about `67%` of the Eq. (4) bottom value.
2. Initial-state mismatch is real, but substituting the raw measured profile
   does not explain away the 8% long-run discrepancy. It worsens the comparison
   if `t=0.002 s` is used directly.
3. The measured initial profile does not significantly improve the analytical
   comparison. Eq. (4) remains the best nominal initial condition.
4. The effective `cv` scale remains close to nominal `cv x 1.12` over the full
   retained window.
5. Bottom-layer averaging has only a minor effect.
6. `PorePressureBoundaryOperator=1` remains useful as an experimental strict
   boundary path, but this audit does not support making it the default.
7. Corrected-gradient PR operators remain deferred.
8. The next step should be calibrated-reference paper figure generation using
   Eq. (4) plus an explicitly reported effective `cv` sensitivity, rather than
   additional MLS/boundary-quadrature source development.
