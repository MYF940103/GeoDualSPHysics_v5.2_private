# q0 k=1e-4 resolution L2 comparison with new dp=0.005 result, 2026-07-13

Purpose: replace the archived incomplete `dp=0.005` comparison with the newer
`CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0005_dt2em6_out` result and
recompute normalized L2 errors at `Tv=0.05`, `0.25`, and `1.0`.

## Inputs

- `dp=0.02`: `tests/outputs/resolution/CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp002_out`
- `dp=0.01`: `CaseTerzaghiConsolidation_q0_PR_full_k1em4_out`
- `dp=0.005`: `CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0005_dt2em6_out`

The new `dp=0.005` output log confirms:

```text
Dp=0.005
FixedDt=0.000002
TimeMax=36.4471428571429
TimePart=0.182185714285714
Finished execution (code=0).
```

## Output files

Generated under:

`tests/figures/resolution_k1em4_dp0005_dt2em6`

- `resolution_k1em4_l2_error.png`
- `resolution_k1em4_profiles.png`
- `resolution_k1em4_targets.csv`
- `resolution_k1em4_profiles_data.csv`
- `resolution_k1em4_observed_orders.csv`
- `resolution_k1em4_dp0005_old_new_compare.csv`

## Key normalized L2 errors

| Tv | dp=0.02 | dp=0.01 | dp=0.005, dt=2e-6 |
| ---: | ---: | ---: | ---: |
| 0.05 | 0.0055486 | 0.0029535 | 0.0024876 |
| 0.25 | 0.0052297 | 0.0064619 | 0.0044450 |
| 1.0 | 0.1060507 | 0.0184323 | 1.2929058 |

The observed order between `dp=0.01` and `dp=0.005` is:

- `Tv=0.05`: `0.248`
- `Tv=0.25`: `0.540`
- `Tv=1.0`: `-6.132`

## Comparison with archived incomplete dp=0.005 run

The new `dt=2e-6` run does not improve the late-time issue relative to the
archived `dt=3e-6` result:

| Tv | old dp=0.005 L2 | new dp=0.005 L2 | new/old |
| ---: | ---: | ---: | ---: |
| 0.05 | 0.0023244 | 0.0024876 | 1.070 |
| 0.25 | 0.0031865 | 0.0044450 | 1.395 |
| 1.0 | 0.8347744 | 1.2929058 | 1.549 |

## Conclusion

The new `dp=0.005`, `DtFixed=2e-6` run is acceptable in the early and middle
windows (`Tv=0.05` and `Tv=0.25`) but fails at `Tv=1`. The late-time profile
keeps too much residual excess pore pressure and gives a much larger error than
the `dp=0.01` baseline. Therefore this result should not be used as evidence of
spatial convergence for the full-time `k=1e-4` q0 Terzaghi case.
