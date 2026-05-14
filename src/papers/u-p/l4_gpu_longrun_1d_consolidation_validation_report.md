# L4 GPU Long-Run 1D Consolidation Validation Report

Date: 2026-05-14

## Objective

L4 extends the L3c consistent initial-state 1D consolidation gate into a GPU
long-run. The target is Level-1 validation: PR pore-pressure diffusion and
hydraulic boundaries under the Terzaghi initial excess-pressure state.

This is not a mechanical top-load reproduction.

## Setup

Experiment directory:

```text
examples/u-pw/01_1D_Consolidation/experiments/ExternalLoad_L4_GPU_LongRun/
```

Case:

```text
Case1DConsolidation_PR_ExternalLoad_L4_GPU_Long_Def.xml
```

Core settings:

| item | value |
| --- | --- |
| `PorePressureInit` | `3` |
| initial excess pressure | `p_w0=10000 Pa` |
| `InitialStressMode` | `0` |
| `PorePressureFeedback` | `0` |
| `AccInput` | disabled |
| `MechanicalTopLoad` | `0` |
| `SoilConstitutiveModel` | `0` |
| `PorePressureBoundaryOperator` | `0` |
| `HydraulicElevationSource` | `1` |
| `TimeMax` | `0.08 s` |
| `TimeOut` | `0.004 s` |

The effective column height inferred from material particles is
`H_eff=0.9900000001 m`. With the current Terzaghi constants,
`c_v=0.2733413500 m2/s`, so the final mapped time factor is:

```text
Tv_final = c_v * TimeMax / H_eff^2 = 2.2311e-2
```

## Runs

GPU Release was run as the main L4 route:

| run | code | excluded | DtMin adjustments | runtime | steps | frames |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GPU | 0 | 0 | 0 | 290.82 s | 83899 | 21 |

A matching L4 CPU long-run was not run. The L3c CPU run already took about
`393 s` for `0.02 s` simulated time, so a matching `0.08 s` CPU run was judged
too expensive for this reporting step. L3c CPU/GPU parity remains the CPU
reference for the same initial-state route.

## Analytical Comparison

L4 retains the correct pressure scale and avoids the L2/L3b dynamic peak:

| metric | L4 GPU |
| --- | ---: |
| peak excess pressure | `10000 Pa` |
| bottom RMSE vs q0 Terzaghi | `9278.64 Pa` |
| final profile RMSE vs q0 Terzaghi | `8712.18 Pa` |
| final bottom excess mean | `1.95e-2 Pa` |
| final max excess | `1.95e-2 Pa` |
| monotonic decay indicator | pass |

The long-run pressure decay is bounded and monotonic, but it dissipates faster
than the Terzaghi analytical reference used in the L3 chain. This is consistent
with the current feedback-off Level-1 gate caveat: L4 is strong evidence for
GPU pressure-update stability and hydraulic-boundary behavior, not a complete
Terzaghi mechanical-storage reproduction.

## Boundary Diagnostics

The hydraulic boundaries remain clean throughout the long-run:

| metric | final L4 GPU |
| --- | ---: |
| top drained residual | `0 Pa` |
| bottom no-flux proxy | `-2.39e-7 Pa` |
| final velocity max | `0 m/s` |
| final `DivVel` maxAbs | `0` |

The top drained layer stays clamped, and the bottom no-flux correction remains
near zero residual after the pressure field has dissipated.

## Consistency With L3c

L4 uses the same Level-1 initial-state route as L3c and extends the run by a
factor of four. The key consistency points are:

- no mechanical dynamic peak;
- peak excess remains at the intended `10 kPa` scale;
- velocity remains zero;
- top and bottom hydraulic boundary diagnostics stay clean;
- GPU completes with `code=0`, `excluded=0`, and no `DtMin` adjustments.

The longer time window makes the analytical mismatch more visible: the current
feedback-off pressure gate dissipates faster than the Terzaghi constrained
storage reference. That does not invalidate L4 as a GPU PR diffusion/boundary
gate, but it prevents presenting L4 as full paper reproduction.

## Figures And Tables

Generated CSV files include:

- `l4_case_summary.csv`;
- `l4_analytical_profiles.csv`;
- `l4_profile_metrics.csv`;
- `l4_bottom_pressure_metrics.csv`;
- `l4_boundary_metrics.csv`;
- `l4_cpu_gpu_parity_metrics.csv`;
- `l4_error_over_time.csv`;
- `l4_tv_mapping.csv`.

Recommended figures:

- `figures/l4_excess_profiles_vs_analytical`;
- `figures/l4_bottom_excess_vs_analytical`;
- `figures/l4_volume_mean_excess_decay`;
- `figures/l4_rmse_vs_tv`;
- `figures/l4_boundary_checks`;
- `figures/l4_level1_vs_level2_schematic`.

## What L4 Validates

L4 validates:

- GPU long-run stability for the PR pressure update;
- top drained boundary behavior;
- bottom no-flux correction behavior;
- bounded monotonic pressure dissipation;
- consistency with the L3c initial-state gate;
- absence of mechanical dynamic waves in the no-load initial-pressure route.

## What L4 Does Not Validate

L4 does not validate:

- mechanical top surcharge generation;
- true surface traction or loading plate behavior;
- full pore-pressure feedback;
- total/effective stress coupling;
- strict full Terzaghi consolidation reproduction.

## Recommendation

L4 can be used as a Level-1 PR diffusion and hydraulic-boundary validation
figure, with the caveat that the feedback-off pressure gate dissipates faster
than the Terzaghi constrained-storage analytical curve over the longer window.

L5 remains required for strict mechanical loading reproduction. Damping or
viscosity sweeps are still not recommended before the loading route and
feedback/stress-coupling scope are clarified.

If the current Level-1 validation coverage is sufficient, the project can move
to the next u-p module. If strict full 1D reproduction remains the priority,
the next step should be L5 CPU-first mechanical loading design.
