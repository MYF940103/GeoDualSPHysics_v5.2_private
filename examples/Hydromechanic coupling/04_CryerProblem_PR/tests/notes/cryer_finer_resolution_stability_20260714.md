# Cryer finer-resolution stability checks, 2026-07-14

Purpose: after the valid CPU Release `dp = 0.0020 m` run improved the
center-pressure peak but still underpredicted the analytical peak, test whether
going finer can be used directly to reduce the remaining peak deficit.

## Reference

The current best valid refinement result is:

- `tests/configs/cpu_release_peak_dp002/CaseCryerProblem_PR_cpu_rel_peak_dp002_Def.xml`
- `tests/figures/cpu_release_peak_dp002/cryer_cpu_release_peak_nu030_dp002_summary.json`

Important values from that valid run:

| Metric | CPU `dp=0.0020` |
| --- | ---: |
| Fluid particles | 71170 |
| Excluded particles | 0 |
| SPH peak `p/q0` | 1.2224858 |
| Theory peak `p/q0` | 1.2490075 |
| Peak deficit | 0.0265216 |
| RMSE | 0.0313029 |

## Tests Tried

All failed direct-refinement tests used the same formal one-stage Cryer setup,
`HydroMechTopLoadMode = FlexibleConfinement`, drainage from `t = 0`, and the
same fixed step as the valid `dp = 0.0020 m` run unless noted otherwise.

| Case | Solver | `dp` | `DtFixed` | Fluid particles | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| `gpu_release_peak_dp0015` | GPU Release | 0.0015 | 5e-6 | 168638 | Invalid: 168622 particles excluded, 144994 by `RhopOut`; >90% excluded by `t=0.010025 s`. |
| `cpu_release_peak_dp0015` | CPU Release | 0.0015 | 5e-6 | 168638 | Invalid: 168635 particles excluded, 147209 by `RhopOut`. |
| `gpu_smoke_dp00175` | GPU Release | 0.00175 | 5e-6 | 106750 | Invalid: 106629 particles excluded, 79035 by `RhopOut`; >90% excluded by `t=0.0082 s`. |
| `gpu_release_peak_dp0019` | GPU Release | 0.0019 | 5e-6 | 84852 | Invalid: 84338 particles excluded, 61770 by `RhopOut`; >90% excluded by `t=0.00911 s`. |
| `cpu_release_peak_dp0019` | CPU Release | 0.0019 | 5e-6 | 84852 | Invalid: 84454 particles excluded, 66125 by `RhopOut`; >90% excluded by `t=0.00911 s`. |

Two reduced-step smoke checks were also started:

| Case | Solver | `dp` | `DtFixed` | Status |
| --- | --- | ---: | ---: | --- |
| `gpu_smoke_dp0015_dt2p5e6` | GPU Release | 0.0015 | 2.5e-6 | Early frames stayed intact: `Part_0000` to `Part_0002`, `PartOut_000.obi4 = 584 bytes`. Stopped manually because full peak-window runtime would be too high for an interactive check. |
| `gpu_release_peak_dp00175_dt2p5e6` | GPU Release | 0.00175 | 2.5e-6 | Early frame stayed intact: `Part_0001` was written and `PartOut_000.obi4 = 584 bytes`. Stopped manually to free the GPU. |

## Interpretation

The next direct resolution step is not usable with the old fixed time step.
`dp = 0.0019 m` is only about 5% finer than `dp = 0.0020 m`, but both CPU and
GPU Release runs fail in the same way: massive early particle exclusion caused
mainly by `RhopOut`. This makes the failure a numerical stability issue in the
current setup, not a GPU-only behavior.

The reduced-step smoke checks indicate that halving the fixed time step can
avoid the immediate blow-up, but the cost becomes high. For example,
`dp = 0.00175 m`, `DtFixed = 2.5e-6 s` needed about 3.6 minutes to reach only
`Part_0001` with the sparse-output setup. A full peak-window comparison would
therefore be much closer to an overnight run than a quick verification.

## Conclusion

Resolution alone cannot currently be pushed below `dp = 0.0020 m` using
`DtFixed = 5e-6 s`. The next accuracy-improvement direction should not be
"simply finer dp at the same time step"; it should be one of the following:

1. Run a planned long reduced-step case, preferably `dp = 0.0019 m` or
   `dp = 0.00175 m` with `DtFixed = 2.5e-6 s`, and output only the peak-window
   snapshots needed for the comparison.
2. Investigate why the pore-pressure/rhop update becomes unstable as soon as
   the particle count rises beyond the `dp = 0.0020 m` case.
3. Revisit the loading/drainage treatment before spending many hours on finer
   meshes, because the valid `dp = 0.0020 m` improvement was real but limited:
   peak deficit remained about `0.0265 p/q0`.

## Cleanup

After recording the conclusions, the failed or manually stopped run products
were removed from `tests/outputs` and `tests/logs`:

- `gpu_release_peak_dp0015`
- `cpu_release_peak_dp0015`
- `gpu_smoke_dp0015_dt2p5e6`
- `gpu_smoke_dp00175`
- `gpu_release_peak_dp00175_dt2p5e6`
- `gpu_release_peak_dp0019`
- `cpu_release_peak_dp0019`

The corresponding XML files under `tests/configs` were kept as reproducibility
records.
