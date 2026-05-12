# LIT-B Supporting Materials Boundary Audit

Date: 2026-05-12

## Scope

This note audits the local Supporting Materials implementation note:

`src/papers/u-p/supporting_information_implementation_notes.md`

and incorporates the A1/A2 findings that the self-weight analytical reference
is a quasi-static one-dimensional consolidation reference, not the raw
particle-level PR equation.

## 1D Consolidation Boundary Definition

For the self-weight verification, the Supporting Materials note describes a
two-stage interpretation:

1. an undrained self-weight stage where pore pressure builds from gravitational
   compression;
2. a drainage stage with top drainage and bottom no-flux.

The one-dimensional analytical solution uses a top-drained, bottom-no-flux
cosine eigenbasis for excess pore pressure dissipation.

In implementation terms used in our current branch:

- top drained means the top boundary/layer excess pressure should be zero after
  drainage activation;
- bottom no-flux means the bottom boundary should not leak hydraulic head or
  excess pressure through the base.

The Supporting Materials note does not provide a general curved-boundary
operator formula.

## Cryer Drained Surface

No additional Cryer-specific drained spherical boundary algorithm was found in
the local Supporting Materials note. The strict Cryer boundary must therefore
be inferred from the main paper's general boundary section, not from the
self-weight Supporting Materials.

## Ghost / MLS / Extrapolation Formula

The Supporting Materials note does not add a formula for:

- boundary-particle pressure ghost values;
- moving least-squares pressure extrapolation;
- curved drained surface quadrature;
- center-pressure extraction for Cryer.

Those details are in the main paper's general boundary section, or absent from
the available local notes.

## Center Pressure / Normalized Comparison

The local Supporting Materials note is focused on self-weight consolidation and
does not define the Cryer center-pressure extraction algorithm. For Cryer, our
current center extraction plan remains based on the C2/C3-B postprocessing
design: fixed geometric center, nearest and small-radius averaged particle
values, normalization by `p0`, and comparison against the analytical reference.

## Boundary Layer Handling

For the self-weight validation, the current implementation uses production
layer controls:

- top drained layer correction;
- bottom no-flux layer correction;
- Shepard smoothing on material pressure;
- optional experimental boundary operators.

A1/A2 showed that Scenario 2's residual discrepancy is mostly not controlled by
these layer corrections. This self-weight conclusion should not be overextended
to Cryer: the strict Cryer problem needs a curved drained exterior surface, and
the Supporting Materials do not supply that missing implementation detail.

## Analytical vs Numerical Boundary Consistency

The Supporting Materials analytical solution assumes ideal one-dimensional
boundary conditions. The numerical production implementation approximates them
through layer controls. A1/A2 already established that the self-weight
analytical curve is a quasi-static reference and not a direct reconstruction of
the raw PR particle equation.

For Cryer, the gap is larger: the analytical solution assumes an exactly
drained spherical exterior surface, while the current C5d implementation only
uses virtual spherical Dirichlet samples coupled to material particles.

## Audit Conclusion

The Supporting Materials do not justify continuing the C5d quadrature path as a
faithful reproduction of the paper. They support the 1D self-weight top-drained
/ bottom-no-flux interpretation, but they do not provide a curved Cryer
boundary operator. The next Cryer boundary design should rely on the main
paper's boundary-particle / MLS description rather than on self-weight layer
logic.
