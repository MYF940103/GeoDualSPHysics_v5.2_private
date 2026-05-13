# C5n Corrected Laplacian Design

## Scope

C5n adds one CPU-only experimental subroute to the existing
`PorePressureBoundaryOperator=3` curved drained sphere path:

`CurvedDrainedBoundaryMode=8`

Mode `8` is a boundary-aware corrected Laplacian prototype for the pressure
diffusion operator. It is not a production strict Cryer boundary, it is not a
new governing equation, and it does not change modes `0` to `7`.

Mode `6` radial-shell flux correction and mode `7` conservative shell exchange
are frozen as diagnostics. C5k/C5m showed that matching integrated flux or
shell bookkeeping alone does not fix the near-boundary pressure field.

## Why Mode 6 And 7 Failed

Mode `6` made the outer boundary flux more finite-volume-like, but the surface
shell stayed far above the FV radial diffusion reference. At `dp=0.010`, the
global flux ratio became reasonable while the final surface shell mean remained
about `577 Pa` versus the FV `85.9 Pa`.

Mode `7` forced conservative shell storage balance to machine precision, but
the pressure-only gate still failed. At `dp=0.008`, it developed late apparent
flux reversal and a large pressure-rate artifact. This means the failure is not
only missing global conservation; the local near-boundary `LapPorePress`
operator is inconsistent on the curved support.

## Current Operator

The material-material PR pressure diffusion path computes an SPH Laplacian of
the form:

```text
LapP_i += 2 V_j (p_i - p_j) (r_ij . grad W_ij) / (|r_ij|^2 + eps)
```

For a complete interior support this preserves constants and is reasonable for
smooth radial fields. C5l showed that `u=1` gives zero residual and `u=r^2` is
good in the interior. Near the spherical boundary, however, the support is
truncated, and the same operator develops a strong negative bias. For `u=r^2`,
the near-boundary p95 absolute error was about `12.24`, `14.06`, and `17.08`
for `dp=0.010`, `0.008`, and `0.0065`.

## Candidate Corrections

Four candidates were considered:

- MLS second-order polynomial reconstruction;
- corrected kernel-gradient divergence;
- local least-squares Laplacian recovery;
- boundary-constrained polynomial reconstruction.

C5n chooses the smallest auditable version: a local quadratic MLS Laplacian
recovery applied only near the curved drained boundary.

## Mode 8 Numerical Form

For each near-boundary material particle `i`, local coordinates are defined as:

```text
xi = x_j - x_i
```

Mode `8` fits:

```text
p(xi) ~= a0 + a1 xi_x + a2 xi_y + a3 xi_z
       + a4 xi_x^2 + a5 xi_y^2 + a6 xi_z^2
       + a7 xi_x xi_y + a8 xi_x xi_z + a9 xi_y xi_z
```

The recovered Laplacian is:

```text
Laplacian(p_i) = 2 (a4 + a5 + a6)
```

The implementation uses scaled local coordinates `xi / support`, then converts
the quadratic coefficient sum back by dividing by `support^2`.

## Boundary Constraint

Mode `8` includes material neighbors and tangential samples on the physical
sphere. For the strict pressure-only drained gate with
`HydraulicElevationSource=0`, the boundary value is:

```text
p_b = 0
```

Those boundary samples participate in the local least-squares system as
Dirichlet data. They do not carry dummy volume, and they do not overwrite any
material particle pressure.

## Fallback And Diagnostics

Mode `8` records:

- target count;
- corrected count;
- fallback count;
- material and boundary sample counts;
- condition estimate statistics;
- recovered Laplacian magnitude;
- replaced `LapPorePress` magnitude.

If the system is under-sampled or ill-conditioned, the default fallback keeps
the existing material-only `LapPorePress`. This is intentional: failure should
be visible in diagnostics rather than silently clamping the material pressure.

## Expected Gate

C5n must pass two gates before any compression smoke:

1. Manufactured radial fields: especially `u=r^2` and a drained-like `R-r`
   field near the boundary.
2. Pressure-only spherical diffusion versus the C5i FV reference.

If the pressure-only gate fails, Cryer compression and C6 Figure 7B comparison
remain blocked.
