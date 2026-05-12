# C5 Strict-Sphere Cryer Coarse Smoke

## Objective

C5 tests whether the strict-Cryer building blocks can run together in one
coarse CPU sphere:

- `SoilConstitutiveModel=0` linear elastic skeleton;
- `FlexibleConfiningStress=1` spherical free-surface compression candidate;
- `PorePressureBoundaryOperator=3` with `PorePressureCurvedDrained=1`;
- `HydraulicElevationSource=0` gravity-free hydraulic representation.

This is a module-integration smoke, not a quantitative reproduction of Cryer
Figure 7B and not a Poisson-ratio sweep.

## Case Setup

Retained case directory:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5_StrictSphere_CoarseSmoke/`

The retained passing run uses:

| item | value |
|---|---:|
| geometry | filled 3D sphere, no explicit boundary particles |
| radius `R` | `0.05 m` |
| spacing `dp` | `0.01 m` |
| particles | `739` material particles |
| Poisson ratio | `0.3` |
| elastic modulus | `2e6 Pa` |
| `ConfiningStressP0` | `50 Pa` |
| ramp | `0` to `0.0005 s` |
| `TimeMax` | `0.006 s` |
| `TimeOut` | `0.001 s` |

The physical constants are coarse-smoke values inherited from the C4-D
stability tests. They are not the final values for Figure 7B reproduction.

## Run Result

| metric | value |
|---|---:|
| code | `0` |
| excluded | `0` |
| steps | `56` |
| runtime | `1.94 s` |
| frames | `7` |
| final time | `0.006032 s` |
| `Kplastic` max | `0` |
| final max velocity | `1.06e-3 m/s` |

The log confirms that the linear elastic skeleton was active and DP yield,
return mapping, plastic increment, `Kplastic` accumulation, and softening were
bypassed.

## Module Checks

`FlexibleConfiningStress` was active with `p0_eff=50 Pa` and `739` target
particles. During the ramp diagnostics, the maximum confining acceleration was
`1.95 m/s2`, the center-of-mass acceleration estimate stayed below
`2.46e-8 m/s2`, and the symmetry residual stayed below `2.30e-8`.

The curved drained boundary was active with `592` near-surface affected
particles. The operator diagnostic reported `boundary_residual_max=0 Pa` for
the drained ghost state. This is not a post-update clamp: the material
near-surface shell can still carry nonzero pore pressure, reaching
`263 Pa` max absolute excess in this coarse smoke.

`HydraulicElevationSource=0` was active. The diagnostic `LapZ` field is still
computed, but the used `LapZ` contribution to `PorePressRate` is zero in the
retained CSVs.

## Center Pressure Response

The averaged center pressure rises under compression:

| time [s] | averaged center `p_w` [Pa] | `p_w/p0` |
|---:|---:|---:|
| `0.000000` | `0.0` | `0.00` |
| `0.001005` | `22.42` | `0.45` |
| `0.002011` | `383.60` | `7.67` |
| `0.004022` | `126.74` | `2.53` |
| `0.006032` | `146.17` | `2.92` |

This is qualitatively Mandel-Cryer-like in the limited sense that the center
pressure rises above the applied `p0` and then begins to dissipate/rebound in
the coarse short window. The overshoot magnitude is not quantitative; it is
strongly affected by the coarse free sphere, provisional material constants,
and first-order curved drained ghost prototype.

An analytical `nu=0.3` curve is included only as context in the generated
figure. No C5 error metric should be interpreted as Figure 7B validation.

## Important Limitation Found During C5 Tuning

Exploratory extensions beyond the retained `0.006 s` window entered a coarse
free-sphere oscillatory/out-check regime. A 0.02 s exploratory run completed
but approached the onset of particle loss, and a 0.05 s extension produced
excluded particles. Those exploratory runs were not retained as passing C5
results.

This means C5 proves that the four CPU modules can work together in a short
coarse sphere, but it is not yet ready for C6 quantitative comparison.

## Generated Files

- `c5_strict_sphere_case_summary.csv`
- `c5_center_pressure_history.csv`
- `c5_boundary_residual_metrics.csv`
- `c5_flexible_confining_stress_metrics.csv`
- `c5_pressure_rate_terms.csv`
- `figures/c5_*.(svg|png)`

The heavy solver output directories were removed after analysis.

## Recommendation

C5 should be treated as a passing short integration smoke with a clear
limitation. The next step should be C5b geometry/time-window refinement before
C6 quantitative reference comparison. C5b should address the coarse free-sphere
oscillation/out-check behavior and improve the drained exterior representation
or extraction window. GPU remains deferred because `FlexibleConfiningStress`,
mode `3`, and `HydraulicElevationSource=0` are CPU-only in this route.
