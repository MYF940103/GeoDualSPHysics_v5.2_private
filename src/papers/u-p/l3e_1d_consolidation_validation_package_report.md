# L3e 1D Consolidation Validation Package Report

Date: 2026-05-14

## Objective

L3e consolidates the 1D consolidation validation chain from L1 through L3c.
This stage adds no new simulations and no source changes. It organizes the
existing evidence into a package for deciding which curves can be used as
validation figures and which routes remain reduced smoke tests.

## Cases In The Package

The package summarizes:

1. L1 external-load baseline;
2. L2 paper-aligned `AccInput` setup;
3. L3a initial-pressure diffusion gate;
4. L3b CPU `MechanicalTopLoad` force-on-material prototype;
5. L3c consistent initial-state gate.

The generated package directory is:

```text
examples/u-pw/01_1D_Consolidation/experiments/L3e_ValidationPackage/
```

## What Is Validated

The L3a/L3c route validates:

- PR pore-pressure diffusion update;
- top drained excess-pressure boundary;
- bottom no-flux correction;
- CPU/GPU consistency for the pressure-only gate;
- Terzaghi initial-state excess-pressure decay trend.

L3c is the best current validation figure route because it states the
consistent Terzaghi initial condition explicitly:

```text
p_w0 = |q0| = 10 kPa
InitialStressMode = 0
AccInput = disabled
MechanicalTopLoad = disabled
PorePressureFeedback = 0
```

## What Is Not Validated

The package does not validate:

- mechanical top-load generation;
- true surface traction or force-controlled loading plate behavior;
- full hydromechanical feedback;
- damping or viscosity sensitivity;
- full paper reproduction of the loading stage.

## Key Evidence

### Dynamic Loading Routes Are Not Strict Validation

L2 and L3b are stable but not Terzaghi-faithful:

| case | route | peak excess | bottom RMSE | final profile RMSE |
| --- | --- | ---: | ---: | ---: |
| L2 CPU | `AccInput` body acceleration | 6.246e5 Pa | 2.206e5 Pa | 4.791e4 Pa |
| L3b CPU | top material force | 5.897e5 Pa | 2.724e5 Pa | 4.401e5 Pa |

Both routes over-generate pressure by roughly two orders of magnitude relative
to the `10 kPa` analytical load scale.

### Initial-State Route Is The Clean Gate

L3a and L3c eliminate the dynamic peak:

| case | route | peak excess | bottom RMSE | final profile RMSE |
| --- | --- | ---: | ---: | ---: |
| L3a CPU | initial pressure | 1.000e4 Pa | 7.287e3 Pa | 9.129e3 Pa |
| L3c CPU | consistent initial state | 1.000e4 Pa | 7.287e3 Pa | 9.129e3 Pa |
| L3c GPU | consistent initial state | 1.000e4 Pa | 7.287e3 Pa | 9.129e3 Pa |

L3c matches L3a because the physically consistent feedback-off Terzaghi initial
condition is uniform excess pore pressure with zero effective-stress increment.

### Boundary Checks Are Clean

Final L3c boundary diagnostics:

| run | top drained residual | bottom no-flux proxy |
| --- | ---: | ---: |
| CPU | 0 Pa | 2.34e-3 Pa |
| GPU | 0 Pa | 2.32e-3 Pa |

The hydraulic boundary implementation is reliable for the reduced validation
gate.

### CPU/GPU Parity

The pressure gate is GPU-supported. L3c CPU and GPU have the same peak excess
and nearly identical bottom/profile RMSE values:

- peak excess difference: `0 Pa`;
- bottom RMSE difference: about `1.1e-2 Pa`;
- final profile RMSE difference: about `9.2e-3 Pa`.

## Figures And Tables

Recommended main figures:

- `l3e_bottom_excess_routes_vs_analytical`;
- `l3e_l3c_profiles_vs_analytical`;
- `l3e_error_peak_comparison`;
- `l3e_boundary_residual_comparison`;
- `l3e_loading_route_schematic`.

Recommended supplementary figures:

- `l3e_cpu_gpu_parity`;
- `l3e_velocity_diagnostics`;
- L3c initial excess and profile figures retained in the L3c directory.

Recommended tables:

- `l3e_case_inventory.csv`;
- `l3e_summary_metrics.csv`;
- `l3e_loading_route_comparison.csv`;
- `l3e_cpu_gpu_comparison.csv`.

## Final Recommendation

Use L3c as the current paper-compatible PR diffusion and hydraulic-boundary
validation figure.

Do not use L2 or L3b as strict validation curves. They are stable reduced
smoke/diagnostic cases whose loading routes generate unrealistic pressure
peaks.

Do not start a damping or viscosity sweep yet. The evidence points to loading
route fidelity as the dominant blocker.

Mechanical top-load reproduction should be deferred to L3d. If the current
diffusion/boundary validation coverage is sufficient, the project can move to
the next u-p module.
