# C4-C Drained Curved Pore-Pressure Boundary Report

Date: 2026-05-12

## Objective

C4-C adds a CPU-only drained curved pore-pressure boundary prototype for the
future strict Cryer sphere. The goal is not to run strict Cryer, but to verify
that a spherical exterior drained condition can enter the PR hydraulic operator
through `LapPorePress` and `LapZ`.

## Implementation Summary

The new interface is `PorePressureBoundaryOperator=3` with
`PorePressureCurvedDrained=1`.

Mode `3` is CPU-only. GPU execution with mode `3` or
`PorePressureCurvedDrained=1` hard-errors during XML loading, avoiding a silent
fallback to mode `0`.

The implementation:

- selects material particles in a spherical near-surface shell;
- constructs an outward Dirichlet ghost state;
- uses `excess=0` by default for drained pore pressure;
- adds the ghost contribution to `LapPorePress` and `LapZ` before
  `PorePressRate`;
- does not clamp material `PorePress` after the pressure update;
- leaves modes `0`, `1`, and `2` unchanged.

## Build

- CPU Release: passed.
- CPU Debug: passed.
- GPU Release: passed; mode `3` remains unsupported at runtime.

## Smoke Cases

Smoke directory:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/drained_curved_boundary_C4C/`

| Case | Purpose | Result |
|---|---|---|
| `CaseC4C_CurvedDrained_Zero` | no-source stability under mode `3` | `code=0`, `excluded=0` |
| `CaseC4C_CurvedDrained_Diffusion` | pressure-only uniform-excess drainage smoke | `code=0`, `excluded=0` |
| `CaseC4C_CurvedDrained_Compression` | flexible confining stress plus drained curved boundary | `code=0`, `excluded=0` |

All three cases use a small free sphere (`R=0.05 m`, `dp=0.01 m`, `739`
material particles) and `SoilConstitutiveModel=0`.

## Metrics

Summary CSVs:

- `c4c_drained_boundary_case_summary.csv`
- `c4c_drained_boundary_residual_metrics.csv`
- `c4c_pressure_diffusion_metrics.csv`
- `c4c_compression_drainage_metrics.csv`
- `c4c_confining_stress_diagnostics.csv`

Key final metrics:

| Case | Final time [s] | Final maxAbs excess [Pa] | Surface maxAbs excess [Pa] | `Kplastic` max | Notes |
|---|---:|---:|---:|---:|---|
| zero | 0.002011 | 490.50 | 490.50 | 0 | `PorePressRate=0`; nonzero excess reflects the hydrostatic reference because current PR requires positive `HydraulicGravity`. |
| diffusion | 0.020008 | 1052.57 | 963.17 | 0 | Surface excess decayed from 1000 Pa to 963 Pa; interior remained higher. |
| compression | 0.005027 | 383.46 | 383.46 | 0 | Compression produced early positive center excess, then short free-sphere elastic oscillation. |

Flexible confining stress diagnostics for the compression smoke:

- final logged `p0_eff = 50 Pa`;
- target particles: `739`;
- total absolute confining force: `1.66413 N`;
- max confining acceleration: `1.95492 m/s2`;
- center-of-mass acceleration estimate: `2.08e-08 m/s2`;
- symmetry residual: `1.94e-08`.

## Figures

Generated figures include:

- boundary excess residual proxy;
- center excess pressure;
- mean excess pressure;
- maxAbs excess pressure;
- velocity max;
- surface radial velocity;
- `PorePressRate` max;
- `LapPorePress` max;
- `Kplastic` max;
- operator boundary residual;
- radial excess-pressure profiles;
- radial `PorePressRate` profiles;
- radial `LapPorePress` profiles.

## Interpretation

Mode `3` is more than a clamp: the drained curved boundary contribution is
assembled before the PR rate evaluation and appears in the hydraulic operator
diagnostics. The pressure-only smoke shows outward surface drainage: the
surface excess decreases while the interior remains elevated.

The compression smoke confirms compatibility with the CPU
`FlexibleConfiningStress` candidate. The center pore pressure becomes positive
early under compression, `Kplastic` remains zero, and the run remains stable.
The later sign change is a short free-sphere elastic oscillation, so this smoke
should not be interpreted as a Cryer center-pressure curve.

## Remaining Limitations

- The current PR formulation still requires positive `HydraulicGravity` for the
  hydraulic diffusivity scale, so a fully gravity-free Cryer formulation remains
  unresolved.
- Mode `3` is a spherical Dirichlet ghost prototype, not a general MLS curved
  boundary method.
- GPU support is not implemented.
- No strict Cryer analytical comparison was run.
- No long run was performed.

## Recommendation

C4-C is sufficient to proceed to a **coarse CPU strict Cryer smoke** only if the
next phase explicitly treats it as a formulation smoke, not as final Figure 7
reproduction. Before claiming strict reproduction, the no-elevation hydraulic
representation and center-pressure analytical comparison still need to be
resolved.
