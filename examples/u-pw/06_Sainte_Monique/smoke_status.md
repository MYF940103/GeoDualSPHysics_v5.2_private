# Smoke Status: Sainte-Monique Reduced Placeholder PR Case

Date: 2026-05-11

## Case

- XML: `CaseSainteMonique_PR_ReducedSmoke_Def.xml`
- Launcher: `xCaseSainteMonique_PR_ReducedSmoke_win64_CPU_debug.bat`
- Solver path tested: CPU Release
- TimeMax: `0.0002 s`
- TimeOut: `0.0002 s`
- Analysis: `analyze_sainte_smoke.py`

## Execution

| Check | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics | code=0 |
| Excluded particles | 0 |
| Steps | 34 |
| Runtime | 0.61 s solver / 1.36 s end-to-end |
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
| Max velocity | `1.9849e-3 m/s` |
| Mean velocity | `6.3462e-4 m/s` |
| Max displacement | `2.1000e-7 m` |
| Mean displacement | `6.4404e-8 m` |
| PorePress min/max | `0 / 3196.09 Pa` |
| ExcessPorePress min/max | `0 / 8.77 Pa` |
| PorePressRate max | `1.19e5 Pa/s` |
| DivVel min/max | `-2.80e-4 / 0 1/s` |
| Kplastic min/max | `0 / 0` |

## Interpretation

The reduced placeholder smoke is stable and field-complete for CPU case
readiness. It is not a validated Sainte-Monique reproduction because field data,
zoning, sensitive clay calibration, and full-scale GPU workflow are missing.

Generated output was removed after recording these metrics.
