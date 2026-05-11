# B5 GPU Pore-Pressure Boundary Operator Report

Date: 2026-05-11

## Objective

Port the CPU `PorePressureBoundaryOperator=1` prototype to the GPU path and
test whether operator-level top drained and bottom no-flux boundary
contributions improve the self-weight Scenario 2 analytical comparison.

The default remains:

- `PorePressureBoundaryOperator=0`: legacy post-update layer correction.

The new optional path is:

- `PorePressureBoundaryOperator=1`: boundary-consistent PR operator prototype.

`mode=2` remains reserved and unsupported.

## Implementation Summary

Modified GPU-side source files:

- `source/JSph.cpp`
- `source/JSphGpu.h`
- `source/JSphGpu.cpp`
- `source/JSphGpu_ker.h`
- `source/JSphGpu_ker.cu`

The previous GPU hard error for `PorePressureBoundaryOperator=1` was removed.
The GPU now logs the selected boundary operator mode.

For `mode=1`, the GPU PR diagnostic path adds boundary contributions after the
material-material `LapPorePress` / `LapZ` calculation and before
`PorePressRate` is used:

- Top drained: excess-pressure Dirichlet ghost, `excess=0`.
- Bottom no-flux: hydraulic-head / excess-pressure Neumann mirror ghost.
- The total-pressure gradient is not set to zero at the bottom.

The legacy top drained and bottom no-flux layer projections remain active after
the pore-pressure update as safety corrections, matching the CPU `mode=1`
prototype.

## Build Status

- GPU Release build: passed.
- CPU Release build: passed.

No CPU `mode=0` behavior was intentionally changed.

## B4 Short/Medium Validation

All B4 tests were run in:

`examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_B4_BoundaryOperator/`

Summary:

| Test | Result |
|---|---:|
| GPU hydrostatic, `mode=1` | `code=0`, `excluded=0` |
| CPU/GPU pressure-only, `mode=1` | `code=0`, `excluded=0` |
| CPU/GPU self-weight short, `mode=1` | `code=0`, `excluded=0` |
| GPU self-weight medium, `mode=1`, `TimeMax=0.05 s` | `code=0`, `excluded=0` |

Selected metrics:

- Hydrostatic `mode=1`: top excess maxAbs `0 Pa`; bottom proxy
  `3.42e-7 Pa`; `PorePressRate` maxAbs `33.1 Pa/s`.
- CPU/GPU pressure-only `mode=1`: final `PorePress` maxAbs difference
  `4.11e-3 Pa`.
- CPU/GPU self-weight short `mode=1`: final `PorePress` maxAbs difference
  `2.21e-3 Pa`.
- GPU self-weight `mode=1` versus GPU `mode=0` over the short window:
  final `PorePress` maxAbs difference `1.15e-4 Pa`; pressure-rate differences
  are localized to the diagnostic operator and do not destabilize the run.

Conclusion: GPU `mode=1` matches CPU `mode=1` closely for pressure fields and
is stable enough to evaluate in a long Scenario 2 run.

## B5 Long Run

Run directory:

`examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_B5_BoundaryOperatorLong_Xi005/`

Setup:

- GPU Release only.
- `TimeMax=3.6 s`, `TimeOut=0.1 s`.
- `HydromechDampingXi=0.05`.
- `PorePressureBoundaryOperator=1`.
- Other hydromechanical settings match G9b `xi=0.05`.

Result:

| Metric | Value |
|---|---:|
| code | `0` |
| excluded | `0` |
| steps | `3,775,438` |
| runtime | `9,668.14 s` |
| frames | `37` |
| final max excess | `1110.26 Pa` |
| final mean excess | `695.40 Pa` |
| final bottom mean excess | `1110.09 Pa` |
| final top drained excess maxAbs | `9.47e-7 Pa` |
| final bottom no-flux proxy | `3.02e-3 Pa` |
| final/peak excess-envelope ratio | `0.06986` |

The long run is stable and maintains `code=0`, `excluded=0`.

## Analytical Comparison

Comparison files:

- `gpu_b5_boundary_operator_frame_metrics.csv`
- `gpu_b5_boundary_operator_case_summary.csv`
- `gpu_b5_boundary_vs_analytical_metrics.csv`
- `gpu_b5_boundary_vs_analytical_profile_timeseries.csv`
- `gpu_b5_boundary_vs_analytical_bottom_timeseries.csv`

Figures:

- `figures/gpu_b5_mode0_mode1_vs_analytical_porepress_profiles.svg/png`
- `figures/gpu_b5_mode0_mode1_vs_analytical_excess_profiles.svg/png`
- `figures/gpu_b5_bottom_porepress_time.svg/png`
- `figures/gpu_b5_bottom_excess_time.svg/png`
- `figures/gpu_b5_excess_envelope.svg/png`
- `figures/gpu_b5_excess_error_vs_depth_t3p6.svg/png`
- `figures/gpu_b5_boundary_layer_error_decomposition.svg/png`

The analytical reconstruction follows the same formulation used for the G9/G9b
comparison. The existing G9b `mode=0` raw particle CSV files were cleaned after
that phase, so mode=0 profile curves are recovered approximately from retained
SVG profiles; B5 `mode=1` profiles are computed directly from retained raw
PartCsv output before cleanup.

Bottom time-series metrics against analytical:

| Line | Bottom excess RMSE | Relative RMSE |
|---|---:|---:|
| GPU `mode=0`, `xi=0.05` | `550.17 Pa` | `0.07594` |
| GPU `mode=1`, `xi=0.05` | `550.18 Pa` | `0.07594` |
| GPU `mode=0`, `xi=0.10` | `585.50 Pa` | `0.08081` |

Final excess-profile metrics at `t=3.6 s`:

| Line | Full-domain RMSE | Bottom-region RMSE |
|---|---:|---:|
| GPU `mode=0`, `xi=0.05` | `74.02 Pa` | `90.12 Pa` |
| GPU `mode=1`, `xi=0.05` | `215.33 Pa` | `260.01 Pa` |

The time-series bottom error is essentially unchanged by `mode=1`. The
late-time profile comparison is worse for the current `mode=1` ghost
contribution, especially near the bottom region.

## Interpretation

`PorePressureBoundaryOperator=1` is successfully implemented and stable on GPU,
but this first material-layer ghost contribution does not reduce the
Supporting-Materials analytical discrepancy for Scenario 2. The approximately
8% bottom excess relative RMSE remains effectively unchanged.

The result suggests that the current analytical mismatch is not solved by this
simple operator-level boundary contribution alone. Possible remaining causes
include:

- analytical reconstruction assumptions;
- drainage path / initial self-weight excess alignment;
- kernel-support and layer-projection effects;
- the need for a more complete boundary quadrature, MLS, or mDBC-compatible
  pore-pressure boundary treatment.

## Decisions

- `mode=0` should remain the production default.
- `mode=1` should remain optional and experimental.
- Do not promote `mode=1` as the default strict reproduction path yet.
- Do not run `xi=0.10`, `mode=1` long-run by default; the `xi=0.05` comparison
  already shows negligible time-series improvement and worse profile metrics.
- Corrected-gradient PR production remains deferred.

## Recommended Next Step

Before any GPU production promotion, audit the analytical reconstruction and
design a stronger boundary treatment that includes a more complete
boundary-particle/ghost quadrature or MLS-style pressure reconstruction. The
current GPU `mode=1` implementation is valuable as a parity-tested prototype
but should not be treated as the final strict boundary operator.
