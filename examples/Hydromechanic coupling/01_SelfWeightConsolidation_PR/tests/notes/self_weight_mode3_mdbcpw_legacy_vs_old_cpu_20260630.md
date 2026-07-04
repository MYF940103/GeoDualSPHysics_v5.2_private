# Mode 3 GPU versus old CPU control comparison

Case: `CaseSWScenario2_Mode3_MdbcPwLegacy_GPU`

## Result

- Status: `DIFFERENT`
- Bottom dissipation max abs difference: `9.85507 kPa`
- Bottom dissipation RMS difference: `7.70279 kPa`
- Target-point max abs bottom difference: `9.75458 kPa`
- Target-point max abs RMS-profile difference: `5555.83 Pa`
- Target-point max abs speed difference: `0.00105346 m/s`

## Decision

GPU Mode 3 differs from the previous CPU Mode 3 reference beyond the current engineering tolerance. Do not start the two-stage Mode 3 workflow yet; first check CPU/GPU path differences or code changes affecting HydroMechInitMode=3.

## Files

- `figures\CaseSWScenario2_Mode3_MdbcPwLegacy_GPU_vs_old_cpu\mode3_gpu_vs_cpu_bottom_dissipation_compare.csv`
- `figures\CaseSWScenario2_Mode3_MdbcPwLegacy_GPU_vs_old_cpu\mode3_gpu_vs_cpu_target_compare.csv`
- `figures\CaseSWScenario2_Mode3_MdbcPwLegacy_GPU_vs_old_cpu\mode3_gpu_vs_cpu_summary.csv`
- `figures\CaseSWScenario2_Mode3_MdbcPwLegacy_GPU_vs_old_cpu\mode3_gpu_vs_old_cpu_bottom_compare.png`
