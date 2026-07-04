# Self-weight fixed-Dt semantics repair, 2026-07-01

## Context

The old CPU Mode3 baseline for Scenario 2 used a prescribed fixed time step:

- `DtFixed=1e-6 s`
- `PoreDtSafety=0.1`
- `TimeMax=3.85 s`
- output interval `0.02 s`

In the current code before this repair, both CPU and GPU computed the fixed time
step first and then applied the pore-pressure diffusion limit:

```cpp
if(FixedDt) dt = FixedDt->GetDt(TimeStep, dt);
dt = min(dt, dtw);
```

This changed the meaning of `DtFixed`: the actual time step could become smaller
than the prescribed fixed value whenever `dtw < DtFixed`.

## Repair

`JSphCpu::DtVariable()` and `JSphGpu::DtVariable()` were changed so that a
prescribed fixed time step is used as prescribed. The pore-pressure diffusion
limit is applied only to variable time stepping:

```cpp
if(FixedDt) dt = FixedDt->GetDt(TimeStep, dt);
else dt = min(dt, dtw);
```

## Verification

- CPU Debug build completed successfully.
- GPU Release build completed successfully.
- Short Mode3 GPU replay to `t=0.2 s` completed with strict fixed-step output:
  `Part_0001` at 20000 steps, `Part_0009` at 180000 steps.
- The short GPU replay matches the old CPU Mode3 baseline:
  - bottom-pressure max absolute difference over the available targets:
    `0.008125 kPa`
  - at `Tv=0.0494001`, current GPU bottom excess pressure:
    `8.106178 kPa`
  - at the same `Tv`, old CPU bottom excess pressure:
    `8.106054 kPa`

## Current status

A full Mode3 GPU replay using the repaired fixed-Dt logic completed under:

`tests/outputs/CaseSWScenario2_Mode3_FixedDtAfterCode_GPU_full_out`

The full-run comparison against the old CPU Mode3 baseline reports `MATCH`:

- `Steps of simulation=3850000`
- `PART files=193`
- `Excluded particles=0`
- bottom-pressure max absolute difference over the full curve:
  `0.0081285 kPa`
- bottom-pressure RMS difference over the full curve:
  `0.0008757 kPa`
- at `Tv=0.998981`, current GPU bottom excess pressure:
  `0.793858 kPa`
- at the same `Tv`, old CPU bottom excess pressure:
  `0.794671 kPa`

Therefore the old CPU pore-pressure profile accuracy is restored by repairing
the fixed-time-step semantics. The previously tested mDBC pore scheduling,
merged pore-rate loop, free-surface drainage predicate, CteB/Cs0, artificial
viscosity, damping, and mDBC corrector paths are not the controlling cause of
the old/current mismatch.

Main evidence:

- `tests/figures/CaseSWScenario2_Mode3_FixedDtAfterCode_GPU_full/scenario2_pore_pressure_profiles.png`
- `tests/figures/mode3_after_fixeddt_code_gpu_full_vs_old_cpu/mode3_current_vs_old_cpu_bottom_compare.png`
- `tests/figures/mode3_after_fixeddt_code_gpu_full_vs_old_cpu/mode3_gpu_vs_cpu_summary.csv`
- `tests/figures/mode3_after_fixeddt_code_gpu_full_vs_old_cpu/mode3_gpu_vs_cpu_target_compare.csv`
