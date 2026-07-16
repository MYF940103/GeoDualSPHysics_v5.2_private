# Lian flexible strip timestep sensitivity - 2026-06-27

Case: `05_LianFlexibleStrip2D_PR`

Compared two 3 s GPU runs with the same geometry, loading, drainage mask, free-slip mDBC command, and no diffusion:

- Baseline/economical run: `dt=5e-5`, `TimeOut=0.05 s`
- Smaller timestep run: `dt=2e-5`, `TimeOut=0.05 s`

Outputs:

- Baseline: `tests/outputs/CaseLianFlexibleStrip2D_PR_gpu3s_dp01_dt5e5_damp004_nodiffusion_lianstrip_out`
- Smaller dt: `tests/outputs/CaseLianFlexibleStrip2D_PR_gpu3s_dp01_dt2e5_damp004_nodiffusion_lianstrip_out`
- Comparison figures/CSV/JSON: `tests/figures/figures_timestep_dt5e5_vs_dt2e5`

Main numerical differences, computed by matching fluid particles by `Idp`:

| Target time | Base max EPWP (kPa) | Test max EPWP (kPa) | Mean abs diff (kPa) | RMS diff (kPa) | Max abs diff (kPa) | Max diff / base max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 s | 2.563533 | 2.563557 | 5.41e-06 | 7.17e-06 | 4.25e-05 | 1.66e-05 |
| 1.0 s | 4.208078 | 4.208076 | 1.89e-06 | 3.29e-06 | 2.81e-05 | 6.67e-06 |
| 3.0 s | 1.715155 | 1.715166 | 1.75e-05 | 2.30e-05 | 1.10e-04 | 6.43e-05 |

A/B point EPWP curves are visually indistinguishable between the two timesteps. At 3 s:

- A: 0.895632 kPa (`dt=5e-5`) vs 0.895702 kPa (`dt=2e-5`)
- B: 0.897341 kPa (`dt=5e-5`) vs 0.897401 kPa (`dt=2e-5`)

Decision:

- Use `dt=5e-5` for the 50 s long run because the smaller timestep did not produce a meaningful accuracy change in the 3 s check.
- The measured 3 s wall times were similar: 2153.69 s (`dt=5e-5`) and 2166.90 s (`dt=2e-5`), so the validated larger timestep is still the safer economical choice.

Long-run status:

- Started variant: `gpu50s_dp01_dt5e5_damp004_nodiffusion_lianstrip`
- Output directory: `tests/outputs/CaseLianFlexibleStrip2D_PR_gpu50s_dp01_dt5e5_damp004_nodiffusion_lianstrip_out`
- Log prefix: `tests/logs/run_gpu50s_dp01_dt5e5_damp004_nodiffusion_lianstrip_*`
- Command parameters: `DtFixed=5e-5`, `TimeMax=50`, `TimeOut=0.05`, `PoreDtSafety=0.1`, postprocess targets `0.5,1.0,3.0,50.0`
- Early solver status: advanced to `Part_0002` without excluded particles; estimated finish around 2026-06-27 13:46 local time.

Follow-up after the 50 s run:

- The completed `dt=5e-5` full run showed noticeable late-time oscillations in the second half of the dissipation stage.
- For the formal release rerun, the root case XML and GPU BAT were changed to `DtIni=DtFixed=1e-5`, `TimeMax=50 s`, and the same `TimeOut=0.05 s`.
- The new formal output variant is `gpu50s_dp01_dt1e5_damp004_nodiffusion_lianstrip`.
