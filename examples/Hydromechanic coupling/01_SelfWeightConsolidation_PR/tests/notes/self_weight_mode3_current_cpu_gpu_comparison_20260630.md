# Mode 3 GPU versus old CPU control comparison

Case: `CaseSWScenario2_Mode3_current_CPU_vs_GPU`

## Result

- Status: `MATCH`
- Bottom dissipation max abs difference: `0.00263223 kPa`
- Bottom dissipation RMS difference: `0.000653191 kPa`
- Target-point max abs bottom difference: `0.00138721 kPa`
- Target-point max abs RMS-profile difference: `0.936397 Pa`
- Target-point max abs speed difference: `7.32387e-07 m/s`

## Decision

GPU Mode 3 and the previous CPU Mode 3 reference are close enough to treat as the same numerical path. Proceed with the two-stage Mode 3 workflow: Stage 1 analytical-init undrained relaxation, then Stage 2 restart drainage.

## Files

- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_current_cpu_vs_gpu_compare\mode3_gpu_vs_cpu_bottom_dissipation_compare.csv`
- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_current_cpu_vs_gpu_compare\mode3_gpu_vs_cpu_target_compare.csv`
- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_current_cpu_vs_gpu_compare\mode3_gpu_vs_cpu_summary.csv`
