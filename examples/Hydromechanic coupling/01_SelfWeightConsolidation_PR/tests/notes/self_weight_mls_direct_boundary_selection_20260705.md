# Self-weight mDBC pore-pressure boundary selection, 2026-07-05

## Purpose

Stop using the temporary pairwise head-Neumann Darcy substitution as the formal pore-pressure-rate operator, and decide which mDBC pore-pressure reconstruction should be kept for the self-weight consolidation verification.

## Compared boundary treatments

1. Zeroth-order mDBC pore-pressure extrapolation.
   - Strength: slightly smaller bottom-pressure/profile errors in the retained `0.02/0.02` two-stage run up to `Tv=1`.
   - Weakness: poor linear-field recovery at the bottom mDBC boundary.

2. First-order MLS reconstruction of excess pore pressure `q = PorePress - PorePress0` at the boundary/ghost point, with
   `PorePress_b = PorePress0_b + q_MLS`.
   - Strength: recovers the diagnostic linear excess-pore-pressure field to roundoff.
   - Weakness: in the full self-weight run, the bottom residual at late time remains slightly larger than the zeroth-order reference.

3. Head-space MLS / pairwise head-Neumann variants.
   - Strength: physically attractive as a direct hydraulic-head Neumann statement.
   - Weakness: the tested window did not improve the late plateau, and the pairwise substitution makes the Darcy operator too local compared with the usual SPH support-domain summation.

## Selected implementation

Keep the first-order MLS reconstruction of excess pore pressure:

```text
q = PorePress - PorePress0
PorePress_b = PorePress0_b + q_MLS
```

Then let this constructed boundary pore pressure participate directly in the standard SPH Darcy/laplacian summation. Do not replace each boundary pair with a local pairwise `pwp1 + rho_w g dz` value in the formal implementation.

This is the best compromise among the tested options:

- it is first-order consistent for boundary extrapolation;
- it preserves the conventional SPH pair summation structure;
- it avoids the overly local pairwise Neumann substitution;
- it is more physical than the zeroth-order boundary value, even though the 1D benchmark error is not uniformly smaller.

## Code changes retained

- `source/JSphCpu.cpp`
  - In both pore-pressure-rate paths, mDBC boundary neighbours now use `porepress[p2]` in the Darcy term.
  - The MLS mDBC pore-pressure correction remains unchanged.

- `source/JSphGpu_ker.cu`
  - The GPU pore-pressure-rate kernel now mirrors the CPU direct-boundary-pore-pressure Darcy term.

Build checks:

- CPU Debug build passed.
- GPU Release build passed.

## Re-run

New test configs/BAT files:

- `tests/configs/CaseSWSt1_MLSDirect_Def.xml`
- `tests/configs/CaseSWSc2_MLSDirect_Tv2_Def.xml`
- `tests/xCaseSWSt1_MLSDirect_win64_GPU.bat`
- `tests/xCaseSWSc2_MLSDirect_Tv2_win64_GPU.bat`

Correction after review:

- The first full `MLSDirect` run was not a valid `SlipMode=2` test, because the BAT files still passed `-mdbc` on the solver command line.
- That command-line option overrode the XML `SlipMode=2` setting and produced `SlipMode="DBC vel=0"` in `Run.out`.
- The old outputs and figures were therefore renamed with the suffix `_cmdmdbc_override`.
- The BAT files were corrected so mDBC/SlipMode/MDBCCorrector are controlled by XML only.

The corrected `SlipMode=2` run must be regenerated before using the `MLSDirect` result as the final comparison.

Stage 1:

- Output: `tests/outputs/CaseSWSt1_MLSDirect_GPU_out`
- Figures: `tests/figures/CaseSWSt1_MLSDirect`
- Selected restart: `Part_0040`, `t = 0.200 s`
- Reason: lowest Stage 1 pore-pressure RMS against the undrained theoretical profile.

Scenario 2:

- Output: `tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0040_GPU_out`
- Figures: `tests/figures/CaseSWSc2_MLSDirect_Tv2_from_p0040`
- Completed to `Tv = 2`
- Excluded particles: 0

Representative target comparison:

| Tv | Theory bottom EPWP kPa | MLS direct kPa | Error kPa | RMS profile Pa |
|---:|---:|---:|---:|---:|
| 0.000 | 10.696 | 10.403 | -0.293 | 46.1 |
| 0.005 | 9.889 | 9.966 | 0.077 | 96.7 |
| 0.100 | 6.912 | 6.992 | 0.080 | 53.0 |
| 0.500 | 2.537 | 2.656 | 0.119 | 81.8 |
| 1.000 | 0.739 | 0.865 | 0.127 | 86.2 |
| 1.500 | 0.215 | 0.573 | 0.358 | 242.6 |
| 2.000 | 0.063 | 0.555 | 0.492 | 338.1 |

The full result is essentially consistent with the previous `MLSg2` full run. It still shows a late residual plateau, so MLS boundary reconstruction alone does not solve the remaining late-time low-gradient discrepancy. Since the user decided not to keep chasing the final plateau in this work window, the physically consistent MLS-direct method is retained.

## Comparison outputs

Additional comparison files:

- `tests/figures/boundary_method_compare_20260705/boundary_method_target_compare.csv`
- `tests/figures/boundary_method_compare_20260705/boundary_method_summary.csv`
- `tests/figures/boundary_method_compare_20260705/boundary_method_bottom_dissipation_compare.png`
- `tests/figures/CaseSWSc2_MLSDirect_Tv2_from_p0040/mls_direct_vs_root_zero_order_bottom_targets.csv`
- `tests/figures/CaseSWSc2_MLSDirect_Tv2_from_p0040/mls_direct_vs_root_zero_order_bottom_dissipation.png`
- `tests/figures/CaseSWSc2_MLSDirect_Tv2_from_p0040/mls_direct_vs_zero_order_profiles.png`

Temporary live-check VTK and figure directories were removed after the full postprocessing finished.

## Corrected SlipMode=2 full comparison

After removing the solver-side `-mdbc` override from the MLSDirect BAT files, the corrected run used the XML boundary settings:

- `Boundary=2`
- `SlipMode=2` / `No-slip`
- `MDBCCorrector=1`
- Stage 1 `HydraulicConductivity=0`, `SoilDampingCoef=0.02`, `PoreShepardInterval=40`
- Stage 2 `HydraulicConductivity=0.001`, `SoilDampingCoef=0.02`, pore Shepard disabled

Corrected Stage 1 selected `Part_0056`, `t = 0.280 s`, because it retained a low profile RMS while reducing the maximum velocity much more than the pure RMS minimum at `Part_0040`.

Corrected Scenario 2 output:

- `tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out`
- `tests/figures/CaseSWSc2_MLSDirect_Tv2_from_p0056`

Corrected comparison products:

- `tests/figures/boundary_method_compare_20260705_corrected/boundary_method_target_compare_corrected.csv`
- `tests/figures/boundary_method_compare_20260705_corrected/boundary_method_summary_corrected.csv`
- `tests/figures/boundary_method_compare_20260705_corrected/boundary_method_bottom_dissipation_compare_corrected.png`
- `tests/figures/boundary_method_compare_20260705_corrected/boundary_method_bottom_error_compare_corrected.png`
- `tests/figures/boundary_method_compare_20260705_corrected/boundary_method_profiles_common_Tv_compare.png`
- `tests/figures/boundary_method_compare_20260705_corrected/boundary_method_profiles_head_window_compare.png`

Summary metrics from `boundary_method_summary_corrected.csv`:

| Method | Max Tv | Bottom MAE kPa | Max bottom abs error kPa | Late Tv>=1 MAE kPa | Mean profile RMS Pa |
|---|---:|---:|---:|---:|---:|
| root zero-order Tv2 | 2.0 | 0.134 | 0.449 | 0.280 | 101.2 |
| accepted zero-order Tv1 | 1.0 | 0.094 | 0.295 | 0.107 | 61.3 |
| MLS head window | 1.3 | 0.108 | 0.177 | 0.108 | 74.1 |
| MLS direct p56 Tv2 | 2.0 | 0.176 | 0.499 | 0.328 | 112.5 |
| MLS qghost p40 Tv2 | 2.0 | 0.182 | 0.498 | 0.328 | 113.1 |

Interpretation:

- MLS direct and previous MLS qghost/direct-boundary-Darcy results are nearly identical in this 1D self-weight benchmark.
- MLS first-order reconstruction remains more physically consistent for boundary extrapolation and recovers the linear boundary diagnostic much better than zeroth-order reconstruction.
- The complete consolidation benchmark does not show a numerical accuracy gain from MLS. The retained zero-order reference remains slightly closer to the Terzaghi 1D curve, especially at late time.
- Therefore, MLS is justified on consistency grounds, not because this particular benchmark proves a smaller error.

## MLS runtime observation

The corrected MLSDirect `Tv=2` GPU run was slower than the retained zero-order reference and the previous MLSg2 run:

| Run | Steps | Runtime s | Steps/s | Notes |
|---|---:|---:|---:|---|
| corrected MLSDirect p56 Tv2 | 7,287,429 | 25,176.65 | 289.45 | XML `SlipMode=2` |
| previous MLSg2 Tv2 | 7,287,429 | 23,076.76 | 315.79 | earlier full MLS run |
| accepted zero-order Tv1 | 3,850,000 | 12,044.14 | 319.66 | available to Tv=1 |

The slowdown should not be attributed only to MLS pore-pressure reconstruction, because `SlipMode=2` and runtime variability also changed. However, code inspection confirms a real redundant cost in the current integrated mDBC correction:

- CPU `InteractionMdbcCorrectionT2`: the same `a_corr2/a_corr3` matrix is assembled once, but the pore-pressure branch computes determinant/inverse and the stress branch computes determinant/inverse again.
- GPU `KerInteractionMdbcCorrection_Fast` and `KerInteractionMdbcCorrection_Dbl`: the same duplicate determinant/inverse pattern exists.

Recommended optimization:

- Compute determinant and inverse once per boundary particle after the neighbor loop.
- Reuse the same inverse for both pore-pressure MLS and stress/rhop/velocity mDBC extrapolation.
- Keep the existing fallback to zeroth-order average when the determinant is too small.
- Do not cache the matrix inverse across timesteps yet, because support composition, active boundary mode, and particle positions can change. Reuse within a single correction call is safe and local.
