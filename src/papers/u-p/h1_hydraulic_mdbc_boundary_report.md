# H1 CPU Hydraulic mDBC Boundary-Particle Prototype Report

Date: 2026-05-12

## Summary

H1 implemented `PorePressureBoundaryOperator=2` as a CPU-only experimental
hydraulic boundary-particle reconstruction path. Legacy mode `0` and simple
virtual-ghost mode `1` are unchanged. GPU mode `2` remains unsupported.

The prototype reconstructs boundary hydraulic state on the fly and adds
boundary-particle quadrature contributions to the production `LapPorePress` and
`LapZ` fields before `PorePressRate` is computed. It does not alter the PR
governing formula, does not promote corrected-gradient diagnostics, and does not
change default behaviour.

## Implementation Notes

Modified source:

- `source/JSph.h`
- `source/JSph.cpp`
- `source/JSphCpu.h`
- `source/JSphCpu.cpp`
- `source/JSphCpuSingle.cpp`

Mode `2` uses:

- mDBC projected boundary location `pos_b + BoundNormal_b` as the hydraulic
  boundary quadrature position when normals are available;
- top drained boundary state `excess_b=0`, `p_b=p_hydro(z_b)`;
- bottom no-flux state reconstructed from nearby material excess pressure,
  representing head/excess Neumann consistency rather than zero total-pressure
  gradient;
- an explicit CPU-only scan over original boundary particles (`0..Npb-1`),
  followed by distance and top/bottom hydraulic classification filters.

The explicit boundary scan was needed because the current PR neighbour path is
material-centric. It keeps modes `0` and `1` untouched and ensures mode `2`
really injects boundary-particle hydraulic quadrature.

## Build

Both builds completed:

- CPU Release: passed.
- CPU Debug: passed, with the existing MSVC `/Gm` deprecation warning only.

No GPU build or GPU run was performed.

## Short CPU Tests

Experiment directory:

`examples/u-pw/02_SelfWeight_Consolidation/experiments/H1_HydraulicMdbcBoundary/`

All H1 short cases completed with `code=0` and `excluded=0`.

### Hydrostatic Cancellation

| mode | code | excluded | max `PorePressRate` | max `LapP/(rho_w g)+LapZ` | top excess maxAbs | bottom excess mean |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 6.2088 | 8.96e-6 | 0 | -9.39e-5 Pa |
| 1 | 0 | 0 | 6.2088 | 8.85e-6 | 0 | -9.39e-5 Pa |
| 2 | 0 | 0 | 9.9341 | 2.50e-5 | 0 | -5.62e-5 Pa |

Mode `2` preserves hydrostatic consistency to a small absolute residual, but it
is slightly worse than modes `0/1` in this reduced column. It is therefore not a
candidate for default production behaviour yet.

### Pressure-Only Diffusion Short

| mode | code | excluded | max `PorePressRate` | max head residual | bottom excess mean |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 3.146e7 | 47.1897 | 2951.78 Pa |
| 1 | 0 | 0 | 3.146e7 | 47.1897 | 2951.78 Pa |
| 2 | 0 | 0 | 3.147e7 | 47.2107 | 2953.37 Pa |

Mode `2` is stable but does not improve this short pressure-only diffusion
metric. The bottom/no-flux proxy is slightly larger in the current prototype.

### Coupled Self-Weight Very Short

| mode | code | excluded | max `PorePressRate` | max head residual | bottom excess mean |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 2.840e8 | 423.402 | 27686.51 Pa |
| 1 | 0 | 0 | 2.840e8 | 423.402 | 27686.51 Pa |
| 2 | 0 | 0 | 2.868e8 | 426.209 | 27812.34 Pa |

Mode `2` remains stable in the very short coupled smoke, but it does not improve
the self-weight response in this geometry and time window.

## Boundary-Particle Participation

The source log for mode `2` confirms real boundary-particle contributions. In
the self-weight short run at startup:

- bottom boundary contributions: 490
- mDBC normals used: 490
- MLS/SPH reconstruction samples: 11900
- fallback reconstructions: 0
- maximum head residual contribution: about `1.3e-13`

This confirms boundary particles are entering `LapPorePress` / `LapZ`
quadrature in mode `2`. The prototype reconstructs hydraulic state on demand
rather than storing persistent boundary `PorePress` arrays.

## Operator Scaling Reference

The H1 experiment also records the O1-revised standalone eigenmode targets:

| mode/model | `s0` |
|---|---:|
| material-only mode `0` | 0.91197 |
| virtual ghost mode `1` | 0.91202 |
| idealized boundary-particle mode `2` target | 0.99529 |
| 1D MLS reference target | 0.99990 |

These standalone diagnostics still indicate that a boundary-particle-aware
hydraulic quadrature can improve idealized eigenmode consistency. The actual
CPU H1 production prototype, however, did not improve the short pressure-only
or self-weight metrics in the reduced column, likely because the available
mechanical boundary particles are side/bottom mDBC particles rather than a
purpose-built hydraulic quadrature layer for the drained free surface.

## Decisions

- Mode `2` was successfully implemented as a CPU-only experimental path.
- Boundary particles do now enter the PR hydraulic operator in mode `2`.
- Hydrostatic cancellation remains finite and stable but is not better than
  legacy mode `0`.
- Pressure-only diffusion and self-weight short runs are stable with
  `excluded=0`, but mode `2` does not improve the tested metrics.
- H1 does not change the A1/A2/P1 conclusion: Scenario 2 nominal analytical
  discrepancy is still best explained by dynamic storage / effective time-factor
  mismatch, not by the legacy layer correction alone.
- Mode `2` should not be ported to GPU yet and should not become the default.
- Corrected-gradient PR production remains deferred.

## Recommended Next Step

Keep mode `2` as a CPU experimental hook. If stricter boundary accuracy is still
needed, the next meaningful step is not an immediate GPU port, but a dedicated
CPU H2 design with explicit hydraulic boundary quadrature particles or a true
MLS reconstruction layer, including top drained free-surface treatment. That
work should first demonstrate better hydrostatic and pressure-only diffusion
metrics than modes `0/1` before any GPU implementation.
