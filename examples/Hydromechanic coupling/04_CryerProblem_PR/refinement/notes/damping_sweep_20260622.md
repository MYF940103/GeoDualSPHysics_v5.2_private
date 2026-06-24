# Cryer early-window SoilDampingCoef sweep

Date: 2026-06-22

## Purpose

Evaluate which `SoilDampingCoef` best reduces the startup pore-pressure oscillation in the `T_v=0.001-0.01` window without noticeably degrading the pore-pressure accuracy.

## Fixed configuration

- `dp=0.0025`
- `k=1e-5 m/s`
- one-stage drained calculation
- `HydroMechTopLoadMode=3` (`FlexibleConfinement`)
- `HydroMechTopLoadRampTime=0`
- `HydroMechDrainage=1`
- `HydroMechDrainageStartTime=0`
- `DtFixed=5e-6 s`
- `TimeMax=0.01 T_v = 0.00910928571429 s`
- `TimeOut=1e-4 T_v = 0.0000910928571429 s`

## Swept values

`SoilDampingCoef = 0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2`

## Output files

- Raw run folders: `refinement/damping_sweep_20260622`
- Metrics CSV: `figures/cryer_k1e5_dp0025_damping_sweep_20260622_metrics.csv`
- Metrics JSON: `figures/cryer_k1e5_dp0025_damping_sweep_20260622_metrics.json`
- Pore-pressure comparison figure: `figures/cryer_k1e5_dp0025_damping_sweep_20260622_tv001_001.png`
- Metrics figure: `figures/cryer_k1e5_dp0025_damping_sweep_20260622_metrics.png`

## Metrics in T_v=0.001-0.01

| SoilDampingCoef | RMSE | MAE | max abs error | mean abs step | max abs step | max speed | p/p0 at T_v=0.001 | p/p0 at T_v=0.01 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.036641 | 0.034199 | 0.095664 | 0.019302 | 0.145311 | 0.042104 | 0.945252 | 1.094788 |
| 0.005 | 0.036517 | 0.034186 | 0.094469 | 0.018712 | 0.142803 | 0.041546 | 0.946447 | 1.094724 |
| 0.01 | 0.036346 | 0.034134 | 0.093292 | 0.018118 | 0.140342 | 0.040996 | 0.947624 | 1.094659 |
| 0.02 | 0.036058 | 0.034050 | 0.090990 | 0.017019 | 0.135556 | 0.039921 | 0.949926 | 1.094430 |
| 0.05 | 0.035339 | 0.033779 | 0.084492 | 0.013966 | 0.122232 | 0.036886 | 0.956424 | 1.091506 |
| 0.1 | 0.034593 | 0.033324 | 0.074914 | 0.010270 | 0.103072 | 0.032399 | 0.966001 | 1.090956 |
| 0.2 | 0.034811 | 0.033791 | 0.059774 | 0.005629 | 0.073850 | 0.025195 | 0.981142 | 1.089571 |

Analytical `p/p0` values:

- At `T_v=0.001`: `1.040916`
- At `T_v=0.01`: `1.129674`

## Interpretation

- Increasing damping from `0` to `0.1` steadily reduces the early oscillation proxy and velocity while also improving RMSE/MAE.
- `0.2` suppresses oscillation most strongly, but the pore-pressure curve shifts downward more visibly and RMSE becomes slightly worse than `0.1`.
- `0.02`, the previous baseline, is stable but not optimal for the `T_v=0.001-0.01` oscillation window.
- `0.05` is a conservative compromise if we want less damping intervention.
- `0.1` is the best balance in this short-window sweep: it gives the lowest RMSE/MAE among tested values while significantly reducing oscillation and speed compared with `0.02`.

## Recommendation

Use `SoilDampingCoef=0.1` for the next short/full validation candidate, while treating `0.05` as a conservative backup. Do not use `0.2` as the default unless the goal is purely to damp startup oscillation, because it starts to show over-damping in the pore-pressure sequence.
