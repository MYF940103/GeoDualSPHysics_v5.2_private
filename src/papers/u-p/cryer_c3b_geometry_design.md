# Cryer C3-B Geometry Design

Date: 2026-05-12

## Objective

Design the geometry required for strict Cryer reproduction. The current C1
baseline is rectangular and cannot be upgraded into strict Cryer by parameter
tuning alone.

## Strict Requirement

The paper benchmark is a poroelastic sphere:

- radius `R=a`;
- drained exterior surface;
- all-around normal traction `p0`;
- center pressure extracted at `R=0`.

## Option 1: True 3D Sphere

Description:

- generate material particles inside a sphere using GenCase `drawsphere`;
- define a boundary shell around the exterior sphere;
- use the exact geometric center as the postprocessing point;
- apply all-around radial traction `p0`;
- impose drained excess pressure on the curved exterior.

Pros:

- matches the paper benchmark geometry;
- center pressure extraction is unambiguous;
- Figure 7B comparison is defensible.

Cons:

- more expensive than the current reduced workflow;
- spherical traction is not currently proven through native XML;
- drained curved pore-pressure boundary is not locked;
- GPU may be needed for useful resolution, but CPU should establish strict
  formulation first.

Initial draft parameters:

- `a = 0.05 m` as a practical first strict-smoke radius if the paper gives no
  numeric Cryer radius;
- `p0 = 10 kPa` as a normalization load if the paper gives no Cryer-specific
  load;
- coarse `dp = a/10` or `a/12` for early XML/prototype checks;
- later resolution study at smaller `dp`.

These values are placeholders until the PDF/reference audit confirms whether a
paper-specific radius or load is available.

## Option 2: Axisymmetric or 2D Surrogate

Description:

- represent the radial response with a cylinder, disk, or 2D axisymmetric-like
  domain;
- apply an approximate outer drained boundary and radial loading.

Pros:

- lower cost;
- useful for debugging pore-pressure response and center extraction.

Cons:

- not the same analytical problem as the paper sphere unless a matching
  axisymmetric reference is derived;
- cannot be cited as strict Figure 7 reproduction by default;
- boundary and traction errors may mask the Mandel-Cryer response.

## Recommended First Strict Route

Use Option 1, a true 3D sphere, for the strict track.

The first implementation should be a coarse 3D sphere skeleton, not a reduced
column/cylinder. It should remain CPU-first until:

- analytical reference curves are generated and checked;
- all-around traction route is confirmed;
- drained curved boundary treatment is selected;
- center pressure extraction is validated on generated output.

An axisymmetric surrogate may still be useful as an intermediate diagnostic,
but it should be labeled reduced and should not replace the strict route.
