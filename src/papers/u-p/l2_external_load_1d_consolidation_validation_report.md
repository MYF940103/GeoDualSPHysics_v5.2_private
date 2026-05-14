# L2 External-Load 1D Consolidation Validation Report

Date: 2026-05-14

## Objective

L2 extends the L1 native-`AccInput` external-load smoke toward a paper-aligned
1D Terzaghi consolidation validation. It is not a damping/viscosity sweep and
does not modify source code.

Experiment directory:

```text
examples/u-pw/01_1D_Consolidation/experiments/ExternalLoad_L2_PaperAligned/
```

## Paper Alignment

L2 aligns the input setup with the u-pw 1D consolidation target:

| Quantity | L2 value |
|---|---:|
| `H` | `1.0 m` nominal, `0.99014 m` particle-center comparison height |
| width | `0.1 m` |
| `Dp` | `0.01 m` |
| `E`, `nu` | `2e6 Pa`, `0.3` |
| `Kw`, `n`, `k` | `2e8 Pa`, `0.3`, `1e-3 m/s` |
| skeleton | `SoilConstitutiveModel=0` |
| top drainage | top excess-pressure drained after load ramp |
| bottom drainage | no-flux layer correction |
| lateral route | periodic 1D column route |
| top load target | `q0=-10 kPa` |
| AccInput mapping | `a_z=-476.190476 m/s2` on `mkfluid=1` top layer |

The analytical script uses Terzaghi single-drainage theory with
`c_v=0.27334 m2/s` from the constrained modulus plus finite-`Kw` storage.

## Changes Relative To L1

L1 proved that native `AccInput` can drive a stable external-load pore-pressure
response. L2 changes the case in three important ways:

- explicitly sets `SoilConstitutiveModel=0`;
- moves hydraulic material constants into `<special><soils>`;
- maps the top-layer acceleration to the paper load `q0=-10 kPa` rather than
  using the small L1 smoke acceleration.

L2 also adds analytical profile, bottom-pressure, boundary, and CPU/GPU
postprocessing.

## Runs

Both short validation runs completed.

| Run | code | excluded | DtMin adjustments | runtime | steps |
|---|---:|---:|---:|---:|---:|
| CPU Release | `0` | `0` | `0` | `548.19 s` | `20,975` |
| GPU Release | `0` | `0` | `0` | `49.06 s` | `20,975` |

No NaN/Inf, particle exclusion, or timestep burst was detected.

## Boundary Checks

The boundary layer corrections behaved well in the short L2 run:

| Run | final top drained residual | final bottom no-flux proxy |
|---|---:|---:|
| CPU | `0 Pa` | `-0.0701 Pa` |
| GPU | `1.76e-4 Pa` | `-0.0711 Pa` |

This is a strong numerical boundary check for the retained layer-correction
route, although it is still not a strict boundary ghost/MLS reproduction.

## Analytical Comparison

The L2 response is bounded and CPU/GPU-consistent, but it is not close to the
paper Terzaghi curve for `q0=10 kPa`.

| Metric | CPU | GPU |
|---|---:|---:|
| target `q0` amplitude | `10,000 Pa` | `10,000 Pa` |
| fitted bottom amplitude | `4.827e5 Pa` | `4.827e5 Pa` |
| peak excess maxAbs | `6.246e5 Pa` | `6.246e5 Pa` |
| final bottom excess mean | `7.814e4 Pa` | `7.814e4 Pa` |
| bottom RMSE vs `q0` Terzaghi | `2.206e5 Pa` | `2.206e5 Pa` |
| final profile RMSE vs `q0` Terzaghi | `4.791e4 Pa` | `4.791e4 Pa` |

The response is therefore much larger and more oscillatory than the analytical
quasi-static `q0=10 kPa` solution. The CPU/GPU match confirms this is a workflow
and modeling-route issue rather than a CPU/GPU discrepancy.

## Error Source

The dominant error is the loading representation:

```text
paper: instantaneous or quasi-static surface surcharge
L2: body acceleration applied to one material top layer
```

At `q0=-10 kPa`, the top-layer AccInput route excites the explicit coupled
mechanics/PR feedback system. This generates a large dynamic excess-pressure
episode before and shortly after top drainage activates.

The error is not primarily from:

- CPU/GPU inconsistency;
- top drained enforcement;
- bottom no-flux enforcement;
- material constant mismatch.

## Figures and Tables

Retained outputs:

- `l2_case_summary.csv`
- `l2_analytical_profiles.csv`
- `l2_profile_metrics.csv`
- `l2_bottom_pressure_metrics.csv`
- `l2_boundary_metrics.csv`
- `figures/l2_excess_profiles_vs_analytical.*`
- `figures/l2_pore_pressure_profiles.*`
- `figures/l2_bottom_excess_vs_analytical.*`
- `figures/l2_bottom_pore_pressure_vs_analytical.*`
- `figures/l2_relative_error_time.*`
- `figures/l2_boundary_checks.*`
- `figures/l2_cpu_gpu_comparison.*`
- `figures/l2_l1_l2_bottom_comparison.*`
- `figures/l2_velocity_max_time.*`

## Validation Status

L2 is more paper-aligned than L1 in setup, load target, skeleton model, and
analytical postprocessing. It is not yet a paper-compatible validation curve.

What L2 validates:

- XML-native external-load case runs on CPU and GPU;
- `SoilConstitutiveModel=0` plus PR pressure update is stable for this short
  paper-load probe;
- top drained and bottom no-flux layer corrections remain numerically clean;
- CPU/GPU outputs are effectively identical for this route.

What L2 does not validate:

- quasi-static Terzaghi response under `q0=-10 kPa`;
- strict surface traction/loading-plate boundary;
- nonperiodic lateral no-flux boundary theory;
- long-time analytical consolidation curve.

## Recommendation

Do not start a broad damping/viscosity sensitivity sweep yet. The mismatch is
too large and is dominated by the reduced AccInput top-layer loading route.

If external-load Terzaghi remains the priority, the next L3 should focus on a
small loading/staging strategy audit:

- gentler or staged surcharge application;
- feedback-off/on diagnostic comparison;
- possible loading plate or traction boundary design.

If the immediate project goal is to advance the u-p module, L2 is sufficient to
document that the current native AccInput route is stable but not paper-level
for `q0=-10 kPa`, and the work can move to the next benchmark/module.
