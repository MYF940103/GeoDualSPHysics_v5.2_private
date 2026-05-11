# B1/B2 CPU Pore-Pressure Boundary Operator Report

## Objective

This phase tested whether the remaining Scenario 2 analytical mismatch is dominated by the current simplified hydraulic boundary treatment. The baseline implementation uses post-update layer projections:

- top drained: reset the top material layer to hydrostatic pressure, i.e. excess pore pressure is zero;
- bottom no-flux: reset the bottom material layer excess pressure to the mean excess pressure in the layer above it;
- PR operators (`LapPorePress`, `LapZ`, `DivVel`) remain material-material only.

The new prototype adds an optional CPU-only boundary contribution to the production PR `LapPorePress` and `LapZ` operators while keeping the legacy layer projection as a safety correction.

## Implemented Switch

Parameter:

```xml
<parameter key="PorePressureBoundaryOperator" value="0" />
```

Modes:

- `0`: legacy layer correction only. This is the default and preserves old behavior.
- `1`: CPU-only boundary-consistent PR operator prototype.
- `2`: reserved, not implemented.

`PorePressureBoundaryOperator=1` is rejected for GPU runs in this branch so CPU/GPU behavior cannot silently diverge.

## Boundary Convention

The operator uses hydraulic elevation `z_h = -x dot g_h/|g_h|`.

Top drained:

- interpreted as an excess-pressure Dirichlet condition;
- virtual boundary state uses `excess_ghost = 0`;
- total ghost pressure uses a linear hydrostatic reference, not the non-negative physical clamp, so a hydrostatic field preserves `LapPorePress/(rho_w*g_h) + LapZ = 0` across the mirrored stencil.

Bottom no-flux:

- interpreted as zero normal hydraulic-head gradient;
- after hydrostatic reference decomposition this is a zero normal excess-pressure gradient for the saturated column tests;
- virtual boundary state mirrors excess pressure: `excess_ghost = excess_i`;
- this is not a zero total pore-pressure-gradient condition.

Corrected-gradient PR diagnostics remain diagnostic-only and are not used by this operator.

## Modified Code

- `source/JSph.h`: added `PorePressureBoundaryOperator`.
- `source/JSph.cpp`: parameter default/read/logging and GPU guard.
- `source/JSphCpu.h`: CPU boundary operator state and declarations.
- `source/JSphCpu.cpp`: CPU top Dirichlet and bottom Neumann virtual contributions to `LapPorePress` and `LapZ`.
- `source/JSphCpuSingle.cpp`: applies mode-1 boundary contributions after material-material `LapPorePress/LapZ` and before PR rate computation.
- `papers/u-p/u_pw_parameters.md`: documented the optional CPU-only boundary operator.

No GPU source files were modified.

## Validation Setup

Directory:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/CPU_B1_BoundaryOperator/
```

The test harness generates paired mode-0/mode-1 cases and writes:

- `boundary_operator_summary_metrics.csv`
- `figures/boundary_operator_hydrostatic_residual.svg/png`
- `figures/boundary_operator_excess_profiles_legacy_vs_new.svg/png`
- `figures/boundary_operator_bottom_excess_legacy_vs_new.svg/png`
- `figures/boundary_operator_error_vs_depth.svg/png`

Build:

```text
CPU Release build: passed
```

All short smoke cases completed with `code=0` and `excluded=0`.

## Summary Metrics

| Test | Mode | code | excluded | max PorePressRate residual | top excess maxAbs | bottom proxy | total RMSE | excess RMSE | bottom excess RMSE | head residual maxAbs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hydrostatic | 0 | 0 | 0 | 6.2088 | 0 | 1.48e-8 | 2.21e-4 | 6.93e-5 | 9.39e-5 | 8.96e-6 |
| hydrostatic | 1 | 0 | 0 | 6.2088 | 0 | 1.48e-8 | 2.21e-4 | 6.93e-5 | 9.39e-5 | 8.85e-6 |
| uniform excess | 0 | 0 | 0 | 4.4208e7 | 0 | 2.45e-2 | 49.322 | 49.322 | 60.693 | 66.312 |
| uniform excess | 1 | 0 | 0 | 4.4208e7 | 0 | 2.45e-2 | 49.322 | 49.322 | 60.693 | 66.312 |
| diffusion profile | 0 | 0 | 0 | 3.1460e7 | 0 | 1.44e-2 | 40.169 | 40.169 | 54.983 | 47.190 |
| diffusion profile | 1 | 0 | 0 | 3.1460e7 | 0 | 1.44e-2 | 40.169 | 40.169 | 54.983 | 47.190 |
| selfweight short | 0 | 0 | 0 | 2.8401e8 | 0 | 2.208e-1 | 17976.936 | 17976.935 | 27686.514 | 423.402 |
| selfweight short | 1 | 0 | 0 | 2.8401e8 | 0 | 2.208e-1 | 17976.936 | 17976.935 | 27686.514 | 423.402 |

## Interpretation

The first version of the virtual boundary contribution exposed an important detail: using the clamped physical hydrostatic pressure at virtual points above the water level breaks hydrostatic cancellation at the top stencil. The implementation was corrected to use a linear hydrostatic reference for virtual operator states. After that correction, mode 1 no longer worsens hydrostatic consistency.

However, the prototype does not materially improve the short pressure-only or self-weight comparisons:

- hydrostatic residual is essentially unchanged and slightly better only at roundoff scale;
- uniform-excess and diffusion-profile RMSE are unchanged;
- bottom no-flux proxy is unchanged;
- self-weight short metrics are unchanged within numerical noise.

This indicates that the current one-ghost-per-material-layer prototype is stable but not yet a stronger analytical boundary treatment than the existing layer projection. It should not be ported to GPU as a production operator in its current form.

## Decision

`PorePressureBoundaryOperator=1` should remain an experimental CPU prototype. It does not justify GPU porting yet.

Recommended next steps before any boundary-operator GPU work:

1. Keep GPU long-run interpretation tied to the current layer correction.
2. Audit the analytical reconstruction and initial condition alignment before attributing the full 8% bottom-excess error to boundary treatment.
3. If a stricter boundary operator is still needed, design a true boundary quadrature/MLS or mDBC-normal-based hydraulic boundary reconstruction rather than promoting this simple virtual-point prototype.
4. Keep corrected-gradient PR operators deferred; this B1/B2 result does not provide evidence that corrected gradients should be promoted ahead of a stronger boundary treatment.

