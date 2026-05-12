# Strict Cryer Loading and Boundary Notes

Strict loading is all-around normal traction `p0` on the spherical exterior.
Do not replace it with gravity, flat top compression, or uniform AccInput.

Open loading blocker:

- C4-B found no existing native XML support for spherical radial traction.

C4-B loading audit:

- `AccInput` is marker-wise acceleration, not area-weighted radial surface
  traction.
- Floating `linearforce` / `angularforce` are total rigid-body force/torque
  routes, not deformable material traction.
- Prescribed motion is displacement control, not the Cryer traction boundary.
- mDBC/cDBC normals are useful geometry information, but are not currently
  connected to a `p0 -> F_i=-p0 A_i n_i` loading route.

Future strict work should therefore implement or otherwise supply a CPU-first
generic radial/spherical traction route before any strict Cryer simulation is
claimed.

Strict hydraulic boundary is drained excess pore pressure on the curved
exterior:

```text
pore pressure = 0 at R=a
```

Because classical Cryer has no gravity-driven elevation source, this is also
zero excess relative to a zero hydrostatic reference. The current code's
`HydraulicGravity` handling must be audited before running this draft: the
diffusion coefficient still needs the `rho_w g` scaling associated with
hydraulic conductivity units, but the `LapZ` elevation-source contribution
should not create an artificial directional source in the sphere.

Current boundary modes:

- mode 0: stable default but not strict curved drained boundary;
- mode 1: GPU-supported experimental simple ghost;
- mode 2: CPU-only hydraulic boundary-particle prototype;
- future MLS/boundary quadrature: possible strict route, not implemented.

First strict attempts should be CPU-first. GPU should wait until reference,
geometry, loading, and boundary are credible.
