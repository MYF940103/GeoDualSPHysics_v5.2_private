# q0 k=1e-4 dp=0.03 resolution L2 comparison, 2026-07-13

Purpose: add a coarse `dp=0.03` control case to the existing `k=1e-4`
resolution comparison and regenerate normalized pore-pressure L2 error plots at
`Tv=0.05`, `0.25`, and `1.0`.

## Case

- XML: `tests/configs/resolution/CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp003_Def.xml`
- BAT archive: `tests/configs/resolution/xCaseTerzaghiConsolidation_q0_PR_full_k1em4_dp003_win64_CPU.bat`
- Output: `tests/outputs/resolution/CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp003_out`
- Run logs: `tests/logs/resolution/CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp003_run.*.log`
- Runner: CPU Release, `DualSPHysics5.2CPU_win64.exe`
- Main settings: `k=1e-4`, `Dp=0.03`, `DtFixed=1e-5`, `TimeMax=36.4471428571429`, `TimeOut=0.182185714285714`
- Log check: `CaseNfluid=99`, `RunMode=Pos-Double - OpenMP(Threads:20)`, `mDBC-FastSingle=False`

## Output files

Generated under:

`tests/figures/resolution_k1em4_dp003_dp0005_dt2em6`

- `resolution_k1em4_dp003_l2_error.png`
- `resolution_k1em4_dp003_profiles.png`
- `resolution_k1em4_dp003_targets.csv`
- `resolution_k1em4_dp003_profiles_data.csv`
- `resolution_k1em4_dp003_summary.csv`
- `resolution_k1em4_dp003_observed_orders.csv`

## Key normalized L2 errors

| Tv | dp=0.03 | dp=0.02 | dp=0.01 | dp=0.005, dt=2e-6 |
| ---: | ---: | ---: | ---: | ---: |
| 0.05 | 0.6770553 | 0.0055486 | 0.0029535 | 0.0024876 |
| 0.25 | 0.5427954 | 0.0052297 | 0.0064619 | 0.0044450 |
| 1.0 | 2.0378381 | 0.1060507 | 0.0184323 | 1.2929058 |

The `dp=0.03` profiles are strongly distorted at all three target times. At
`Tv=0.05`, the numerical average consolidation degree is `0.75299` while the
theoretical value is `0.25162`; at `Tv=1.0`, the profile keeps excessive
residual pore pressure and gives the largest normalized L2 error in the set.

## Conclusion

The `dp=0.03` case is too coarse for this benchmark and should be treated as an
over-coarse failure/control point, not as a valid point in the convergence-rate
fit. It is useful to show the resolution threshold between `dp=0.03` and
`dp=0.02`, but observed orders involving `dp=0.03` are not physically
meaningful.
