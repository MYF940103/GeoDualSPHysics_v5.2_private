# Cryer C4-B Loading Decision Report

Date: 2026-05-12

## Objective

Decide whether strict Cryer all-around spherical traction can be represented by
existing XML/native mechanisms, and if not, define the minimal source route.

## Decision Summary

No existing native route was found for strict spherical traction.

`AccInput`, floating-body forces, prescribed motion, Chrono/MoorDyn routes, and
mDBC/cDBC normals all provide useful infrastructure, but none currently maps a
scalar pressure `p0` to per-particle inward radial surface forces with area
weighting on a deformable poroelastic sphere.

## Answers To C4-B Questions

### 1. Does the current code have native all-around spherical traction?

No. The audited source and examples do not expose a boundary pressure or normal
surface traction input suitable for:

```text
F_i = -p0 A_i n_i
```

on a selected spherical exterior.

### 2. Can AccInput be used for strict Cryer traction?

No. `AccInput` applies uniform linear/angular acceleration to selected marker
groups. It does not know the local spherical normal, does not estimate boundary
surface area, and does not apply a surface traction. It can support reduced
loading smokes, but not strict Cryer `p0`.

### 3. What is the minimal source addition if native support is unavailable?

Recommended minimal feature:

- XML-controlled generic radial/spherical traction block;
- target marker and center/radius;
- pressure magnitude `p0`;
- optional time ramp;
- CPU-first implementation;
- force mapping `F_i=-p0 A_i n_i`;
- mechanical acceleration only;
- no effect on `HydraulicGravity`;
- diagnostics for area, force symmetry, and radial direction.

This should not be named `TopLoad` and should not be restricted to Cryer.

### 4. Should implementation be CPU first?

Yes. Strict Cryer still has hydraulic boundary blockers. A CPU-only traction
prototype with diagnostics is the right next development step before any GPU
port.

### 5. When is GPU support needed?

GPU support is needed only after:

- CPU traction diagnostics are acceptable;
- drained curved hydraulic boundary route is selected;
- center-pressure extraction against analytical reference is ready;
- a coarse CPU strict sphere smoke is credible.

### 6. Required traction diagnostics

Future implementation should report:

- selected surface particle count;
- total associated area;
- net force vector;
- total absolute applied force;
- max/mean radial direction error;
- per-particle traction magnitude range;
- center-of-mass acceleration estimate;
- normalization pressure `p0`.

### 7. Can C4-C drained boundary audit start?

Yes, as a documentation/source-audit task. However, strict simulation should not
start until both traction and drained curved boundary routes are resolved.

### 8. Should traction route be implemented before strict Cryer simulation?

Yes. Without strict spherical traction, the simulation would be a surrogate and
could not be claimed as Cryer Figure 7 reproduction.

### 9. Should strict Cryer simulation remain paused?

Yes. The strict draft XML remains marked as not validated and not ready to run.

## Recommended Next Step

Proceed with C4-C drained curved boundary audit, or start a CPU-only traction
prototype design task if loading is the priority. The most defensible strict
path is:

1. CPU radial/spherical traction prototype with diagnostics;
2. CPU drained curved hydraulic boundary route;
3. coarse CPU strict sphere smoke;
4. center-pressure extraction and analytical comparison;
5. GPU port only after CPU strict behavior is credible.

Corrected-gradient production remains deferred.
