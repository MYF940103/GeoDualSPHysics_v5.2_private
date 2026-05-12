# C5c Curved Drained Boundary Coupling Report

Date: 2026-05-12

## Objective

C5b showed that the coarse strict-sphere Cryer smoke is stable but not ready for
Figure 7B comparison. The strongest remaining signal was a large material
near-surface excess pressure despite a zero curved-ghost diagnostic residual.
C5c therefore tests whether the current `PorePressureBoundaryOperator=3`
Dirichlet ghost is under-coupled to the material surface.

C5c does not claim strict Cryer reproduction. It is a CPU-only boundary-coupling
diagnostic.

## Source Refinement

C5c keeps modes `0`, `1`, and `2` unchanged and extends only the CPU
`PorePressureBoundaryOperator=3` curved drained prototype through
`CurvedDrainedBoundaryMode`:

| Mode | Meaning | Status |
|---:|---|---|
| 0 | Existing first-order spherical Dirichlet ghost | Baseline experimental mode |
| 1 | Strengthened image-style Dirichlet ghost | New CPU experimental diagnostic |
| 2 | Diagnostic material surface drained clamp after pressure update | Diagnostic only, not production |

Mode `1` changes the ghost pressure to an image value relative to the prescribed
drained state. Mode `2` directly resets material particles in the curved drained
shell to the drained value after pressure update. Mode `2` is intentionally a
diagnostic upper-bound test: it is not an operator-consistent production
boundary and should not be used for strict validation.

GPU remains unsupported for mode `3` / curved drained boundary.

## C5b Surface Residual Audit

The old mode-3 ghost was rerun and audited from retained particle fields. At the
final retained frame (`t=0.006032 s`), the `r > 0.85R` material surface layer
shows:

| Statistic | Excess pressure |
|---|---:|
| mean | 179.37 Pa |
| median | 178.06 Pa |
| p95 absolute | 218.47 Pa |
| max absolute | 263.15 Pa |

The residual is systematic, not a single-particle outlier. Radial bins show
positive excess throughout the outer material shell, with the largest value in
the `0.95R-1.0R` bin but elevated values already from `0.6R` outward.

The zero ghost residual from earlier logs only indicates that the prescribed
ghost state itself is zero. It does not prove that the adjacent material surface
particles satisfy the drained condition through time.

## Compression Tests

All C5c compression variants used the same coarse sphere (`R=0.05 m`,
`dp=0.01 m`, `739` particles), `SoilConstitutiveModel=0`, `p0=50 Pa`,
`HydraulicElevationSource=0`, and CPU Release.

| Case | Mode | code | excluded | peak center p/p0 | final center p/p0 | final surface p95 | final surface max |
|---|---:|---:|---:|---:|---:|---:|---:|
| old ghost | 0 | 0 | 0 | 7.672 | 2.923 | 218.47 Pa | 263.15 Pa |
| strengthened ghost | 1 | 0 | 0 | 7.663 | 2.819 | 212.58 Pa | 258.29 Pa |
| diagnostic clamp | 2 | 0 | 0 | 2.218 | 1.571 | 0.00 Pa | 0.00 Pa |

The strengthened image ghost reduces the final surface p95 by only about 2.7%
and the final averaged center pressure by about 3.6%. It does not materially
solve the C5/C5b over-response.

The diagnostic surface clamp strongly reduces both the surface residual and
center pressure, which confirms that drained material-surface coupling is a
major control on the coarse Cryer response. However, because it is a
post-update material reset, it is not an acceptable production boundary.

## Pressure-Only Diffusion Tests

The pressure-only uniform-excess tests isolate the hydraulic boundary without
mechanical loading.

| Case | Mode | code | excluded | final mean excess | final center excess | final surface max |
|---|---:|---:|---:|---:|---:|---:|
| diffusion old | 0 | 0 | 0 | 963.98 Pa | 968.65 Pa | 970.43 Pa |
| diffusion strengthened | 1 | 0 | 0 | 929.28 Pa | 938.40 Pa | 941.97 Pa |
| diffusion clamp | 2 | 0 | 0 | -90.39 Pa | -380.72 Pa | 682.64 Pa |

The strengthened ghost increases the diffusion rate relative to the old ghost,
so the operator-side direction is beneficial. The diagnostic clamp is too
aggressive for pressure-only diffusion: it produces strong oscillatory
overshoot and much larger velocities. This reinforces that a simple material
clamp is only a diagnostic, not a viable strict-boundary implementation.

## Interpretation

The C5b surface residual is systematic. Old mode 3 is under-coupled to the
material surface: the prescribed ghost value is zero, but the material surface
layer remains pressurized.

The strengthened ghost improves the pressure-only diffusion and slightly
reduces the compression residual, but the improvement is too small for C6
quantitative reference comparison. The diagnostic clamp shows that stronger
surface drainage could move the center response toward a lower, more physical
range, but it also introduces non-operator artifacts.

## Recommendation

C5c should not proceed directly to C6. The next step should be a more
principled boundary refinement rather than a Figure 7B comparison:

- improve mode-3 boundary quadrature / multi-sample Dirichlet treatment;
- then repeat the coarse sphere smoke;
- after the boundary is less under-coupled, perform a modest `dp`/geometry
  refinement (C5d);
- keep GPU deferred.

Mode `0` remains the production default. Mode `3` remains CPU experimental.

