# Smoke Status: Retrogressive Slope Reduced PR Case

Date: 2026-05-10

## Case

- XML: `CaseRetrogressiveSlope_PR_ReducedSmoke_Def.xml`
- Launcher: `xCaseRetrogressiveSlope_PR_ReducedSmoke_win64_CPU_debug.bat`
- Solver path tested: CPU Debug
- TimeMax: `0.0002 s`
- TimeOut: `0.0002 s`

## Execution

| Check | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics | code=0 |
| Excluded particles | 0 |
| Steps | 53 |
| Runtime | 3.14 s |
| Material particles | 602 |
| Boundary particles | 1173 |

## Field Output

`PartCsv_0001.csv` included the required u-pw fields:

- `PorePress`
- `ExcessPorePress`
- `PorePressRate`
- `DivVel`
- `LapPorePress`
- `LapZ`
- `DivVelCorr`
- `LapPorePressCorr`
- `LapZCorr`
- `PorePressureAccel`
- `PorePressureAccelDiff`

## Short-Window Metrics

| Metric | Value |
| --- | --- |
| Max velocity | `1.98e-3 m/s` |
| Mean velocity | `1.97e-3 m/s` |
| PorePress min/max/mean | `399.02 / 2561.64 / 1627.12 Pa` |
| ExcessPorePress min/max/mean | `5.64 / 12.09 / 7.97 Pa` |
| PorePressRate max | `1.66e5 Pa/s` |
| DivVel min/max/mean | `-4.41e-4 / -3.31e-5 / -1.73e-4 1/s` |
| PorePressureAccelDiff.z min/max/mean | `-7.63e-3 / 1.09e-2 / 1.52e-3 m/s2` |

## Interpretation

This reduced slope smoke is stable and field-complete for CPU case readiness.
It does not validate retrogression. Strict reproduction remains blocked by
sensitive clay / strain-softening, production boundary treatment, and GPU-scale
runtime needs.

Generated output was removed after recording these metrics.
