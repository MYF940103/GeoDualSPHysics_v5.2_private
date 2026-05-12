# Cryer C4-B2 Traction Route Decision

Date: 2026-05-12

## Objective

C4-B2 revises the strict Cryer loading route. The project will not spend more
time on an `AccInput` patchwise spherical-traction surrogate. The strict track
is redirected to a flexible confining stress route based on the triaxial loading
strategy described in the drained/undrained SPH framework paper.

No source was modified and no simulation was run in this phase.

## Route A: AccInput Patchwise Surrogate

`AccInput` can apply time-dependent imposed acceleration to selected marker
groups. It can also read a time history from an external file. This is useful
for reduced loading workflows such as a top loading layer, and it was enough for
the L1 external-load 1D consolidation baseline.

For strict Cryer, however, the target load is not a marker-wise acceleration. It
is a uniform all-around inward normal traction `p0` on the spherical exterior.

Even with many shell patches and many external CSV files, an `AccInput` route
would remain a patchwise body-force equivalent:

- each marker receives a uniform acceleration, not a continuous pressure
  traction;
- per-particle spherical normals and surface-area weighting must be supplied
  externally;
- the load is mass-weighted by the selected marker particles, whereas Cryer
  specifies surface traction;
- patch seams and marker discretization would become an additional artificial
  approximation;
- it would not be a clean production route for a Poisson-ratio sweep.

Therefore Route A is formally rejected for strict Cryer. It remains only a
possible reduced surrogate for future debugging, not a strict reproduction
candidate.

## Route B: Flexible Confining Stress

The selected route is a flexible confining stress source term. The source paper
uses this approach for triaxial simulations, citing the Zhao et al. flexible
confined boundary condition. Instead of explicitly finding surface particles,
normals, and areas, a confining stress is inserted into the SPH momentum
summation. By kernel symmetry the contribution cancels inside the material; near
free surfaces the kernel truncation leaves an effective boundary pressure.

For strict Cryer this is attractive because:

- Cryer requires all-around compression, not top compression;
- the confining pressure should act normal to whatever free spherical exterior
  the particles define;
- no explicit surface triangulation or area assignment is required in the first
  implementation;
- the route is closer to the paper's SPH loading idea than an `AccInput`
  patchwise shell acceleration.

## Current Project Decision

- Route A (`AccInput` patchwise spherical loading) is rejected.
- Route B (flexible confining stress in the mechanical momentum equation) is the
  strict Cryer loading route.
- The first implementation should be CPU-only and diagnostic-heavy.
- GPU support should wait until the CPU route passes sign, symmetry, and coarse
  loading smoke tests.
- Drained curved pore-pressure boundary support remains a separate blocker.
- Strict Cryer simulation remains paused until both loading and drained boundary
  routes are credible.

