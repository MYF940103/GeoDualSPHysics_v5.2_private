# Smoke Status: Sainte-Monique Reduced Placeholder PR Case

Date: 2026-05-10

## Case

- XML: `CaseSainteMonique_PR_ReducedSmoke_Def.xml`
- Launcher: `xCaseSainteMonique_PR_ReducedSmoke_win64_CPU_debug.bat`
- Solver path tested: CPU Debug
- TimeMax: `0.0002 s`
- TimeOut: `0.0002 s`

## Execution

| Check | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics | code=0 |
| Excluded particles | 0 |
| Steps | 34 |
| Runtime | 1.83 s |
| Material particles | 556 |
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
| PorePress min/max/mean | `494.76 / 3196.09 / 2121.37 Pa` |
| ExcessPorePress min/max/mean | `3.51 / 8.77 / 5.42 Pa` |
| PorePressRate max | `1.19e5 Pa/s` |
| DivVel min/max/mean | `-2.80e-4 / -2.04e-5 / -1.17e-4 1/s` |
| PorePressureAccelDiff.z min/max/mean | `-6.17e-3 / 6.88e-3 / 5.91e-4 m/s2` |

## Interpretation

The reduced placeholder smoke is stable and field-complete for CPU case
readiness. It is not a validated Sainte-Monique reproduction because field data,
zoning, sensitive clay calibration, and full-scale GPU workflow are missing.

Generated output was removed after recording these metrics.
