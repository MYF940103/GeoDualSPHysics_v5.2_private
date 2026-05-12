# Cryer C3-B Drained Curved Boundary Strategy

Date: 2026-05-12

## Requirement

The strict Cryer boundary is a drained pore-pressure condition on the curved
exterior surface of the sphere:

```text
pore pressure = 0 at R=a
```

There is no gravitational hydrostatic reference in the classical Cryer
benchmark. In the current code terminology, this is equivalent to zero excess
relative to a zero hydrostatic field. The condition should be applied
consistently with the PR hydraulic operator, not only as a top/bottom layer
projection after pressure update.

Important source-design issue: the current PR implementation uses
`HydraulicGravity` to define both hydraulic head/elevation behavior and the
`rho_w g` coefficient used with hydraulic conductivity in m/s. Strict Cryer
needs isotropic pressure diffusion without an elevation-source term. C4 must
decide whether this can be represented by existing inputs or whether a small
CPU-only switch is needed to decouple diffusion scaling from `LapZ`.

## Mode 0: Production Layer Correction

Status: production default, CPU/GPU supported.

Use:

- stable reduced workflows;
- existing self-weight validation;
- current C1 Cryer baseline launch workflow.

Limitation:

- top/bottom layer logic does not define a spherical exterior Dirichlet
  boundary;
- not strict Cryer.

## Mode 1: Simple Virtual Ghost

Status: CPU/GPU experimental.

Use:

- possible first comparison if a spherical geometry can be described using
  existing top/bottom-like filters or if the mode is generalized later.

Limitations:

- designed around simple hydraulic layer assumptions;
- not a full curved boundary treatment;
- previous self-weight tests did not justify making it default.

## Mode 2: Hydraulic mDBC Boundary-Particle Prototype

Status: CPU-only experimental.

Use:

- conceptually closest current path for making boundary particles participate
  in hydraulic quadrature;
- possible CPU-only Cryer strict-boundary experiment.

Limitations:

- not ported to GPU;
- not generalized to all curved boundaries;
- H1 tests did not improve self-weight pressure-only or coupled short cases;
- should remain experimental unless Cryer-specific results justify it.

## Future MLS / Boundary Quadrature

Status: not implemented.

Use:

- likely most defensible path for a curved drained exterior boundary after
  sphere geometry and reference curves are locked.

Limitations:

- source development required;
- should not be combined with corrected-gradient production unless a separate
  diagnostic proves it is needed.

## First Strict Attempt Recommendation

For strict Cryer, do not rely on mode `0` alone.

Recommended C4 ordering:

1. implement/verify analytical reference curves;
2. create true 3D sphere geometry draft;
3. audit native spherical traction support;
4. test CPU-only boundary candidates:
   - mode `1` only if it can be applied to the sphere consistently;
   - mode `2` as the current boundary-particle-aware CPU candidate;
   - future MLS only if modes `1/2` cannot satisfy center-pressure behavior.

GPU should wait until the CPU boundary decision is clear. Corrected-gradient
production remains deferred.
