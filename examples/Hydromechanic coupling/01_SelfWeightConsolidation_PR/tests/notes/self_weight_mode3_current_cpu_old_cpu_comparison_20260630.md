# Mode 3 GPU versus old CPU control comparison

Case: `CaseSWScenario2_Mode3_current_CPU_vs_old_CPU`

## Result

- Status: `DIFFERENT`
- Bottom dissipation max abs difference: `0.336422 kPa`
- Bottom dissipation RMS difference: `0.0897098 kPa`
- Target-point max abs bottom difference: `0.238921 kPa`
- Target-point max abs RMS-profile difference: `146.219 Pa`
- Target-point max abs speed difference: `3.21636e-05 m/s`

## Decision

GPU Mode 3 differs from the previous CPU Mode 3 reference beyond the current engineering tolerance. Do not start the two-stage Mode 3 workflow yet; first check CPU/GPU path differences or code changes affecting HydroMechInitMode=3.

## Files

- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_current_cpu_vs_old_cpu_compare\mode3_gpu_vs_cpu_bottom_dissipation_compare.csv`
- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_current_cpu_vs_old_cpu_compare\mode3_gpu_vs_cpu_target_compare.csv`
- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_current_cpu_vs_old_cpu_compare\mode3_gpu_vs_cpu_summary.csv`
