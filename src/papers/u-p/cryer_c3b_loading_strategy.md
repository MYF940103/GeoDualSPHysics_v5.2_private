# Cryer C3-B Loading Strategy

Date: 2026-05-12

## Requirement

Strict Cryer loading is a uniform all-around normal traction `p0` on the
spherical exterior. This differs from:

- 1D consolidation top load;
- gravity loading;
- AccInput acceleration on a top material layer;
- prescribed compression from a flat loading plate.

The loading direction varies with the radial outward normal and points inward
toward the sphere center.

## Route 1: Existing Native Boundary Pressure / Force Input

Status: not yet proven for a spherical pore-elastic soil body in the current
u-pw examples.

Potential advantages:

- would avoid source changes;
- could preserve a pure XML workflow.

Open checks:

- whether DualSPHysics can apply a pressure/traction to a selected boundary
  marker with direction determined by local normals;
- whether this works on material/boundary particles used by the soil
  formulation;
- whether it is compatible with mDBC and u-pw PR output.

## Route 2: AccInput or Loading-Shell Route

Status: available for 1D external-load baseline, but not equivalent to Cryer
traction.

Pros:

- already used in L1 through native XML;
- no source changes.

Cons:

- AccInput is an acceleration applied to a marker group, not a surface traction;
- a single acceleration vector cannot represent all-around radial normal load;
- a shell of loading particles would still need force/normal control to avoid
  turning the benchmark into a contact/compression problem.

Conclusion: useful for reduced diagnostics, not strict Cryer.

## Route 3: Prescribed Boundary Motion

Status: possible in DualSPHysics generally, but not strict Cryer traction.

Pros:

- can compress a sphere if a boundary shell moves inward.

Cons:

- displacement or velocity control changes the benchmark;
- the analytical reference assumes traction `p0`, not prescribed displacement;
- contact dynamics and shell stiffness may introduce non-Cryer effects.

Conclusion: not recommended for strict reproduction.

## Route 4: Minimal Source Support

If no native XML route can apply radial traction to the spherical exterior, a
minimal source feature may be needed later.

Possible minimal feature:

- an XML-controlled spherical traction load with center, radius, marker scope,
  magnitude `p0`, start/end time, and inward radial normal;
- CPU-first implementation;
- no `TopLoad*` resurrection;
- no effect unless explicitly enabled.

This should not be implemented in C3-B. It is a C4 decision after the native
route audit.

## Recommendation

Do not fake Cryer traction as gravity, top compression, or uniform AccInput.

For C4:

1. first audit whether an existing native pressure/force mechanism can apply
   radial traction by marker and normal;
2. if not, design a minimal CPU-only spherical traction feature;
3. only after CPU strict response is credible should a GPU route be considered.
