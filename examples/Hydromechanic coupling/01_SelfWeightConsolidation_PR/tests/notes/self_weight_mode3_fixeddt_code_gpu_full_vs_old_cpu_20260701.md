# Mode 3 current-run versus old CPU control comparison

Case: `Mode3 current GPU after fixed-dt code change, full run`

## Result

- Status: `MATCH`
- Bottom dissipation max abs difference: `0.00812852 kPa`
- Bottom dissipation RMS difference: `0.000875675 kPa`
- Target-point max abs bottom difference: `0.00812852 kPa`
- Target-point max abs RMS-profile difference: `5.46775 Pa`
- Target-point max abs speed difference: `6.35232e-06 m/s`

## Decision

The current Mode 3 run and the previous CPU Mode 3 reference are close enough to treat as the same numerical path. Proceed with the two-stage Mode 3 workflow: Stage 1 analytical-init undrained relaxation, then Stage 2 restart drainage.

## Files

- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_after_fixeddt_code_gpu_full_vs_old_cpu\mode3_gpu_vs_cpu_bottom_dissipation_compare.csv`
- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_after_fixeddt_code_gpu_full_vs_old_cpu\mode3_gpu_vs_cpu_target_compare.csv`
- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_after_fixeddt_code_gpu_full_vs_old_cpu\mode3_gpu_vs_cpu_summary.csv`
- `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR\tests\figures\mode3_after_fixeddt_code_gpu_full_vs_old_cpu\mode3_current_vs_old_cpu_bottom_compare.png`
