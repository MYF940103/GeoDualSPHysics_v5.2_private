# Self-weight Scenario 2 boundary-method comparison: pairwise MLS optimization

Date: 2026-07-05

## Purpose

This test was run after noticing that the MLS mDBC pore-pressure extrapolation duplicated the same corrected-kernel matrix inversion already needed by the mechanical mDBC stress/velocity extrapolation. The local code optimization reuses the inverse correction matrix for pore pressure and stress/velocity within the same mDBC correction pass.

The optimized code was then used to rerun the temporary pairwise head-Neumann Darcy boundary test for the full Scenario 2 duration of `Tv=2`, so it could be compared against:

- the root zero-order reference output,
- the MLS head/qghost full run,
- the MLS direct full run.

## Code status after the comparison

The pairwise Darcy-boundary path was used only as a test variant. After the comparison, the formal source code was restored so that boundary particles participate in the Darcy term through their extrapolated `PorePress` value:

- CPU: `pwp2seep = pwp2`
- GPU: `pwp2seep = pwp2`

The retained source change is the mDBC inverse-matrix reuse inside the MLS mDBC correction path.

## Outputs

Comparison figures and tables:

`tests/figures/boundary_method_compare_20260705_pairwiseopt/`

Key files:

- `boundary_method_summary_pairwiseopt.csv`
- `boundary_method_target_compare_pairwiseopt.csv`
- `boundary_method_bottom_dissipation_pairwiseopt.png`
- `boundary_method_bottom_error_pairwiseopt.png`
- `boundary_method_profiles_pairwiseopt_compare.png`

Pairwise full-run output:

`tests/outputs/CaseSWSc2_HeadN_Tv2_PairwiseOpt_from_p0056_GPU_out`

Pairwise Stage 1 output:

`tests/outputs/CaseSWSt1_HeadN_PairwiseOpt_GPU_out`

## Quantitative comparison

| Method | bottom MAE (kPa) | max bottom error (kPa) | late Tv>=1 MAE (kPa) | mean profile RMS (Pa) | steps/s |
|---|---:|---:|---:|---:|---:|
| root zero-order Tv2 | 0.1343 | 0.4491 | 0.2802 | 101.18 | n/a |
| MLS head/qghost p40 Tv2 | 0.1822 | 0.4982 | 0.3278 | 113.15 | 315.79 |
| MLS direct p56 Tv2 | 0.1760 | 0.4994 | 0.3282 | 112.48 | 289.45 |
| Pairwise MLS p56 Tv2 | 0.1533 | 0.4504 | 0.2814 | 100.54 | 308.97 |

## Conclusions

1. The pairwise MLS test nearly recovers the long-time bottom-dissipation error of the root zero-order reference, but it does not provide a decisive accuracy improvement over the reference.
2. MLS direct and MLS head/qghost improve the idealized boundary linear-field reconstruction, but in this full coupled consolidation case they did not improve the `Tv=2` pressure-dissipation error.
3. The pairwise path is useful diagnostically, but it remains too local to keep as the formal SPH Darcy operator.
4. The shared inverse-matrix optimization removes duplicated determinant/inverse work in the mDBC MLS path and compiled cleanly on CPU/GPU. The measured PairwiseOpt full run used 23586.20 s / 308.97 steps/s versus MLS direct p56 at 25176.65 s / 289.45 steps/s, but this is not a strict one-variable benchmark because the Darcy boundary treatment differs between the two runs.
5. The formal code path should keep boundary particles participating directly through their mDBC-extrapolated `PorePress`, while retaining the shared corrected-kernel inverse matrix.
