# Cryer C2 Drained Curved Boundary Strategy

Date: 2026-05-12

## Boundary Need

The strict Cryer benchmark requires a drained hydraulic condition over the
curved exterior surface of a poroelastic sphere. This is different from the
current one-dimensional top-drained/bottom-no-flux layer correction workflow.
The drained condition should impose zero excess pore pressure at the exterior
surface while the mechanical boundary applies all-around normal traction `p0`.

## Route 0: Production Mode 0 Reduced Boundary

`PorePressureBoundaryOperator=0` is the current production default.

Pros:

- stable;
- CPU/GPU supported;
- already used in the frozen self-weight validation workflow;
- suitable for reduced launch and visualization workflows.

Cons:

- not a strict curved drained boundary;
- post-update layer projection is not equivalent to a spherical exterior
  Dirichlet boundary;
- cannot by itself justify strict Cryer reproduction.

Use for: C1 baseline and C3-A reduced manual-run workflow.

## Route 1: Mode 1 Simple Virtual Ghost

`PorePressureBoundaryOperator=1` is GPU-supported and experimental.

Pros:

- operator-level hydraulic boundary contribution exists;
- available on CPU and GPU;
- can be tested without new source development.

Cons:

- previous self-weight checks did not show material analytical improvement;
- currently designed around simple top/bottom conventions, not a general
  drained sphere;
- still not a verified curved-boundary treatment.

Use for: optional Cryer experiment after a center-pressure reference exists.

## Route 2: Mode 2 Hydraulic Boundary-Particle Prototype

`PorePressureBoundaryOperator=2` is CPU-only and experimental.

Pros:

- boundary particles can participate in hydraulic quadrature;
- uses head/excess conventions rather than total-pressure no-flux;
- conceptually closer to a boundary-particle-aware hydraulic operator.

Cons:

- CPU-only;
- self-weight short checks did not justify GPU port;
- not generalized to arbitrary curved drained surfaces;
- should remain experimental.

Use for: possible CPU-only strict-boundary experiment, not the first GPU route.

## Route 3: Future MLS / Boundary Quadrature

A future MLS or boundary-quadrature route could explicitly reconstruct the
drained surface condition over a curved exterior.

Pros:

- most plausible route for a strict curved drained surface;
- can be designed around the actual sphere geometry.

Cons:

- requires new development;
- not established as a production path in the current branch;
- no current evidence that it is required before reduced Cryer workflow tests;
- should not be mixed with corrected-gradient production work prematurely.

Use for: future strict Cryer development only after the geometry and reference
are locked.

## Recommendation

For now:

- keep the baseline Cryer workflow on mode `0`;
- use mode `1` only as an optional experimental comparison;
- keep mode `2` CPU-only unless a Cryer-specific CPU test shows clear value;
- do not port mode `2` to GPU for Cryer yet;
- keep corrected-gradient production deferred.

Strict Cryer should first lock the reference and geometry. Boundary source
development should come after those two items are unambiguous.
