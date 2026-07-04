# Mode 3 current-run versus old CPU control comparison

Case: `CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU`

## Result

- Status: `DIFFERENT`
- Bottom dissipation max abs difference: `0.334007 kPa`
- Bottom dissipation RMS difference: `0.0930885 kPa`
- Target-point max abs bottom difference: `0.236484 kPa`
- Target-point max abs RMS-profile difference: `146.166 Pa`
- Target-point max abs speed difference: `0.000863525 m/s`

## Decision

The current Mode 3 run differs from the previous CPU Mode 3 reference beyond the current engineering tolerance. Do not start the two-stage Mode 3 workflow yet; first check CPU/GPU path differences or code changes affecting HydroMechInitMode=3.

## Files

- `figures\CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU_vs_old_cpu\mode3_gpu_vs_cpu_bottom_dissipation_compare.csv`
- `figures\CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU_vs_old_cpu\mode3_gpu_vs_cpu_target_compare.csv`
- `figures\CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU_vs_old_cpu\mode3_gpu_vs_cpu_summary.csv`
- `figures\CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU_vs_old_cpu\mode3_current_vs_old_cpu_bottom_compare.png`
