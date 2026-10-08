# Yao 2025 2-D Consolidation: Free-Slip, Damping, and Stress-Diffusion Checks

Date: 2026-06-26

## Fixed Baseline Choice

The formal case has been fixed to:

- `-mdbc_freeslip`
- XML `SlipMode=3`
- `SoilDampingCoef=0.01`
- `DensityDT=0`
- `PoreShepardRegularization=0`

Reason:

- `-mdbc` overrides XML `SlipMode=3` and runs as `SlipMode="DBC vel=0"`.
- The correct command-line option for Yao's free-slip wall condition is `-mdbc_freeslip`.

## Slip-Mode Comparison

Compared:

- `slip1`: `CaseYao2DConsolidation_PR_gpu10s_dp01_damp002_nodiffusion_out`
- `freeslip`: `CaseYao2DConsolidation_PR_gpu10s_dp01_damp002_nodiffusion_slip3_out`

Key A/B results:

| Case | A max | A tmax (s) | A final | B max | B tmax (s) | B final |
|---|---:|---:|---:|---:|---:|---:|
| slip1 | 0.549832 | 0.15 | 0.127125 | 0.337904 | 0.15 | 0.175530 |
| freeslip | 0.546048 | 0.20 | 0.118406 | 0.245986 | 0.30 | 0.178079 |

Conclusion:

- A point is only weakly affected.
- B point early peak is reduced by free-slip, but final value is nearly unchanged.
- Because Yao's setup is closer to free-slip side/bottom supports, subsequent comparisons use `-mdbc_freeslip`.

## Damping Comparison

Compared free-slip/no-diffusion runs:

- `damp0`: `CaseYao2DConsolidation_PR_gpu10s_dp01_damp000_nodiffusion_freeslip_out`
- `damp0.01`: `CaseYao2DConsolidation_PR_gpu10s_dp01_damp001_nodiffusion_freeslip_out`
- `damp0.02`: `CaseYao2DConsolidation_PR_gpu10s_dp01_damp002_nodiffusion_slip3_out`

Temporary diagnostic output, later removed during DDT cleanup:

- `figures_gpu10s_damping_compare/yao2d_ab_compare_normalized_epwp.png`
- `figures_gpu10s_damping_compare/yao2d_ab_compare_summary.csv`

Key A/B results:

| Case | A max | A final | B max | B final |
|---|---:|---:|---:|---:|
| damp0 | 0.575266 | 0.052382 | 0.335762 | 0.335762 |
| damp0.01 | 0.552789 | 0.118421 | 0.253802 | 0.178147 |
| damp0.02 | 0.546048 | 0.118406 | 0.245986 | 0.178079 |

Conclusion:

- `damp0` leaves strong high-frequency oscillations, especially at B after mid-time.
- `damp0.01` and `damp0.02` are nearly identical after the initial transient.
- `0.01` is selected because it stabilizes pore-pressure response while applying the weaker damping.

Final mirror checks at `t=10 s`:

| Case | Fluid max abs mirror diff (Pa) | Bound max abs mirror diff (Pa) |
|---|---:|---:|
| damp0 | 0.004883 | 0.005127 |
| damp0.01 | 0.031799 | 0.031128 |
| damp0.02 | 0.016479 | 0.014709 |

All mirror errors are negligible relative to kPa-scale pore pressure.

## Stress-Diffusion Comparison

Compared with `SoilDampingCoef=0.01` and free-slip:

- no diffusion: `DensityDT=0`
- stress diffusion Form 1: `DensityDT=1`, `DensityDTvalue=0.1`

Output:

- `figures_gpu10s_stressdiff_compare/yao2d_ab_compare_normalized_epwp.png`
- `figures_gpu10s_stressdiff_compare/yao2d_ab_compare_summary.csv`
- `figures_gpu10s_stressdiff_compare/yao2d_stressdiff_epwp_contours_clipped.png`

Key A/B results:

| Case | A max | A final | B max | B final |
|---|---:|---:|---:|---:|
| no diffusion | 0.552789 | 0.118421 | 0.253802 | 0.178147 |
| DDT1 value=0.1 | 60.037844 | -3.978295 | 306.583200 | -4.734702 |

Run warning:

- `PartsOut=350`
- `Excluded particles due to RhopOut=1`
- Particle loss starts early and grows rapidly around `t=7.6-7.9 s`.

Conclusion:

- `DensityDT=1`, `DensityDTvalue=0.1` is not valid for this Yao u-pw consolidation case.
- The cloud comparison shows full-field contamination, not just A/B sampling noise.
- The formal baseline should remain `DensityDT=0`.
- If stress diffusion is still desired, the next safe tests should use much smaller `DensityDTvalue` values or a stress-only diffusion path decoupled from density/pore-pressure stability.

## DDT3 Follow-Up And Cleanup

DDT3 follow-up:

- Variant: `gpu10s_dp01_damp001_stressdiff3_freeslip`
- Settings: `DensityDT=3`, `DensityDTvalue=0.1`, `SoilDampingCoef=0.01`, `-mdbc_freeslip`
- Runtime warning: `DDT:3 is equal to DDT:1 (but applied to the entire fluid) when gravity.z is zero.`
- Runtime warning: DDT full is advised to use several boundary layers when `h/dp > 1.5`.
- The run was stopped after particles started being excluded.
- Last observed saved file before cleanup: `Part_0099`, about 49.5% of the 10 s run.
- Last observed exclusion count: `Particles out = 4`.

Conclusion:

- DDT3 should also be rejected for this case.
- Since zero gravity makes DDT3 equivalent to DDT1 but applied to the entire fluid, it is not expected to fix the DDT1 instability.
- The formal Yao 2-D consolidation baseline remains `DensityDT=0`.

Cleanup:

- Removed DDT-enabled output directories, temporary XML files, logs, and DDT comparison figures.
- Retained the no-diffusion free-slip damping comparison data and figures.
