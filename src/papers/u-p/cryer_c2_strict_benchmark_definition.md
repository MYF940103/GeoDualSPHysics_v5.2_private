# Cryer C2 Strict Benchmark Definition

Date: 2026-05-12

## Objective

Cryer's problem is the multidimensional poroelastic benchmark used in the u-pw
paper to check whether the coupled pore-pressure formulation captures the
Mandel-Cryer effect. A poroelastic sphere is subjected to an all-around normal
surface traction `p0` while the exterior pore-pressure boundary is drained. The
center pore pressure initially reaches the load scale, rises above it, and then
dissipates to zero.

This C2 document defines what would be required before the current reduced
Cryer workflow can be called a strict paper benchmark.

## Strict Paper Benchmark

| Item | Strict target | Current status |
|---|---|---|
| Geometry | 3D poroelastic sphere with radius `R=a`. | Current XML is a reduced rectangular/column-style scaffold, not a sphere. |
| Dimensionality | Fully 3D sphere; axisymmetric setup would need a documented equivalence. | Current case is reduced 2D/plane-strain style. |
| Loading | Uniform all-around normal traction `p0` on the exterior surface. | Current baseline seeds an excess pressure profile; it does not apply all-around traction. |
| Hydraulic boundary | Drained exterior surface over the curved boundary. | Current baseline uses layer-style top/bottom hydraulic controls, not a curved drained boundary. |
| Material constants | Same elastic and hydraulic constants as the 1D Terzaghi setup, except the Poisson-ratio sweep. | Baseline uses the 1D constants for `E`, `n`, `k`, `Kw`, and `rho_w`; geometry/loading remain reduced. |
| Poisson ratios | `nu = 0.1, 0.2, 0.3, 0.45`. | Baseline uses one value, `nu=0.3`. |
| Reference output | Normalized center pressure `p_w(r=0,t)/p0` versus dimensionless time `Tv`. | Current helper reports a near-center pressure proxy only. |
| Qualitative response | Mandel-Cryer nonmonotonic center pressure: rise above initial load scale, then dissipation. | Not established by the current reduced workflow. |

## Geometry Requirements

A strict Cryer candidate must define:

- sphere radius `a`;
- particle spacing and resolution;
- whether a full sphere, hemisphere, or axisymmetric surrogate is used;
- how the exterior curved surface is represented by particles;
- whether boundary particles only constrain mechanics or also carry hydraulic state.

The current `CaseCryer_PR_Baseline_Def.xml` defines a reduced rectangular body
with `sizefx=0.1 m`, `sizefz=0.5 m`, and `Dp=0.01 m`. It is useful as a launch
workflow, but it is not geometrically equivalent to the paper sphere.

## Boundary and Loading Requirements

Strict Cryer needs two different boundary roles at the same exterior surface:

- Mechanical: all-around normal traction `p0`.
- Hydraulic: drained pore pressure, i.e. exterior excess pore pressure is zero.

The current production default `PorePressureBoundaryOperator=0` is appropriate
for stable reduced workflows, but it is not a strict curved drained boundary.
The previous boundary audit concluded that modes `1` and `2` remain
experimental. They should not become default solely for Cryer without a separate
CPU validation.

## Output Requirements

Strict postprocessing should produce:

- center pore pressure `p_w(r=0,t)`;
- normalized center pressure `p_w(r=0,t)/p0`;
- dimensionless time `Tv`;
- radial pore-pressure profiles if the reference is available;
- optional displacement/strain metrics for checking poroelastic consistency.

## Expected Behavior

The center pressure should show the Mandel-Cryer response:

1. an initial center pore-pressure value on the load scale;
2. an additional center pressure rise above the initial value;
3. dissipation toward the drained final state.

The paper compares this behavior for `nu=0.1`, `0.2`, `0.3`, and `0.45`.

## Gap Relative to Current Workflow

The C1 baseline workflow is still reduced because it lacks:

- strict spherical geometry;
- all-around normal traction `p0`;
- drained curved boundary at the exterior surface;
- analytical center-pressure reconstruction;
- normalized time and pressure comparison;
- a Poisson-ratio sweep.

Therefore the current Cryer workflow remains a reduced/manual launch workflow,
not a strict analytical reproduction.
