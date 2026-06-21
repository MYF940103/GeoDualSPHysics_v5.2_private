# Cryer short validation: k=1e-5, no ramp, drainage from start (2026-06-21)

Case: `k1e5_tv008_toutTv001`

- Loading mode: `FlexibleConfinement`
- Load ramp time: `0`
- Drainage start time: `0`
- Resolution: `dp=0.003`
- Hydraulic conductivity: `k = 1e-5 m/s`
- Target range: `T_v = 0.08`
- Output spacing: `Delta T_v = 0.001`
- Physical `TimeOut`: `0.0009109285714 s`
- Physical `TimeMax`: `0.0728742857 s`
- Solver output kept at:
  `refinement/sweep_corrected_20260621/k1e5_tv008_toutTv001/out`

## Time-scale check

With the current material parameters:

- `k=1e-4`: `T_v=1` corresponds to `0.0910929 s`
- `k=1e-5`: `T_v=1` corresponds to `0.910929 s`

Therefore the short run to `T_v=0.08` uses `TimeMax=0.0728743 s`.

## Result summary

For `T_v <= 0.08`, compared with the dense-output `k=1e-4` full run:

| Metric | k=1e-4 | k=1e-5 |
|---|---:|---:|
| RMSE | `0.04360` | `0.04024` |
| MAE | `0.04065` | `0.03969` |
| Max abs. error | `0.08253` | `0.05581` |
| Numerical peak | `1.20724` | `1.20430` |
| Peak Tv | `0.04666` | `0.04800` |
| Theory at numerical peak | `1.24902` | `1.24874` |
| Peak error | `-0.04177` | `-0.04445` |
| Max saved velocity | `0.10623 m/s` | `0.05816 m/s` |
| Final saved velocity | `0.00398 m/s` | `0.000392 m/s` |

## Generated comparison files

- `figures/cryer_k1e5_tv008_toutTv001_paper_axes.png`
- `figures/cryer_k1e4_vs_k1e5_early_Tv008.png`
- `figures/cryer_k1e4_vs_k1e5_early_error_Tv008.png`
- `figures/cryer_k1e4_vs_k1e5_early_Tv008_metrics.json`

## Current conclusion

Reducing hydraulic conductivity from `1e-4` to `1e-5` stretches the physical
time scale by a factor of ten and reduces the sampled early velocity peak and
the maximum early absolute error. However, it does not remove the remaining
underprediction of the Cryer peak: the numerical peak remains about `0.04-0.045`
below the corrected analytical value.

This suggests that lowering `k` helps the transient mechanical response but is
not the primary fix for the peak-amplitude deficit.
