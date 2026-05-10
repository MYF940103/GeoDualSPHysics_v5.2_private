# Smoke Status: Retrogressive Slope Reduced PR Case

Date: 2026-05-11

## Case

- XML: `CaseRetrogressiveSlope_PR_ReducedSmoke_Def.xml`
- Launcher: `xCaseRetrogressiveSlope_PR_ReducedSmoke_win64_CPU_debug.bat`
- Solver path tested: CPU Release
- TimeMax: `0.0002 s`
- TimeOut: `0.0002 s`

## Execution

| Check | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics | code=0 |
| Excluded particles | 0 |
| Steps | 53 |
| Runtime | 0.77 s |
| Particle rows in CSV | 1775 |
| NaN/Inf scan | not detected |

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
| Max displacement | `2.10e-7 m` |
| Mean displacement | `6.75e-8 m` |
| Max velocity | `1.98e-3 m/s` |
| Mean velocity | `6.67e-4 m/s` |
| PorePress min/max | `0 / 2561.64 Pa` |
| ExcessPorePress min/max | `0 / 12.09 Pa` |
| Kplastic min/max | `0 / 0` |

## Interpretation

This reduced slope smoke is stable and field-complete for CPU case readiness.
It does not validate retrogression. Strict reproduction remains blocked by
sensitive clay / strain-softening, production boundary treatment, and GPU-scale
runtime needs.

`analyze_slope_smoke.py` writes `slope_smoke_summary.csv` with displacement,
velocity, pore-pressure, excess-pressure, and `Kplastic` ranges. Generated
output was removed after recording these metrics.
