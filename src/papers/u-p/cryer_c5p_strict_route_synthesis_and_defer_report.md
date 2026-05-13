# C5p Strict Cryer Route Synthesis and Defer Report

Date: 2026-05-13

## Objective

The original target was a strict Cryer reproduction suitable for later
Figure 7B comparison. That target required several prerequisites to be valid
at the same time:

- a linear elastic skeleton route;
- spherical all-around mechanical traction;
- a drained curved hydraulic boundary on the sphere;
- gravity-free/no-elevation pressure diffusion;
- a center-pressure extraction and analytical reference workflow.

C5p is a documentation-only freeze step. No source code, GenCase output,
CPU/GPU run, or PartVTK processing was performed.

## Completed Building Blocks

The strict route produced several useful components:

- `SoilConstitutiveModel=0` for the linear elastic skeleton path;
- CPU `FlexibleConfiningStress` as a spherical traction candidate;
- `PorePressureBoundaryOperator=3` for curved drained boundary development;
- `HydraulicElevationSource=0` for gravity-free/no-elevation PR diffusion;
- Cryer analytical reference scripts and center-pressure postprocessing;
- experimental `CurvedDrainedBoundaryMode` routes from `0` through `8`.

These pieces are retained as infrastructure. They do not together constitute a
validated strict Cryer reproduction.

## Evidence Summary

### C5 Coarse Strict-Sphere Smoke

The first coarse strict-sphere CPU route completed with `code=0`,
`excluded=0`, and `Kplastic=0`. It produced a Mandel-Cryer-like center pressure
rise, but the averaged center peak was `383.60 Pa`, or `7.67 p0`. That is far
above the Cryer `nu=0.3` analytical peak of about `1.249 p0`.

### C5b Ramp, Load, and Averaging Refinement

Slower loading reduced only the early peak; later values stayed near
`7.66 p0`. Lower `p0` scaled the response nearly linearly, so the discrepancy
was not explained by load nonlinearity or plasticity. Center averaging affected
the extracted value but did not remove the excess. Near-surface material
pressure remained a major blocker.

### C5c Surface Residual Audit

The old material-side spherical drained boundary showed a systematic surface
residual, not an isolated outlier. A diagnostic material clamp reduced the
center response, but it was rejected as a production method because it directly
sets material pressure rather than imposing a boundary value problem.

### C5d Multi-Sample Quadrature

Strengthened ghosts and multi-sample spherical quadrature improved the old
mode-3 boundary only slightly. The result showed diminishing returns for
material-side spherical ghost/quadrature changes.

### C5e Boundary-Particle Drained State

Mode `4` introduced selected boundary particles as hydraulic quadrature sites
with prescribed drained value `p_b=0`. The raw mode had the right conceptual
direction but over-drained pressure-only diffusion: final center pressure was
`-97.17 Pa`, with `PorePressRate` maxAbs about `9.38e5 Pa/s`.

### C5f Normalized Boundary-Particle Weighting

Adami-style local partition normalization reduced the pressure-rate artifact
from about `9.38e5` to `3.33e5 Pa/s` and improved some surface residuals. The
center peak remained too high: mode `3` was about `7.66 p0`, raw mode `4` was
about `6.91 p0` with over-drain, and normalized mode `4` was about `7.45 p0`.

### C5g and C5h Geometry Resolution

Geometry refinement showed that sphere resolution matters but is not the main
blocker. Going from `dp=0.010` to `dp=0.008` increased material particles from
`739` to `1213`, reduced roughness standard deviation from `0.00358` to
`0.00303`, and reduced the center peak from `7.448 p0` to `7.058 p0`.

The higher `dp=0.0065` diagnostic used `2601` material particles but had worse
surface quality, with roughness standard deviation `0.00365`. The center peak
fell to `6.731 p0`, still far above the analytical peak, while the surface
residual and pressure-only diffusion worsened. Final pressure-only center
pressure rose to `746.40 Pa`, and final surface p95 reached `1023.40 Pa`.

### C5i Radial FV Reference and Flux Calibration

C5i established the finite-volume spherical diffusion reference:

- `R=0.05 m`;
- `u0=1000 Pa`;
- `cv=0.0067957866 m2/s`;
- Dirichlet `u(R)=0`.

At `t ~= 0.00603 s`, the FV reference gives center pressure about
`999.998 Pa`, volume mean about `615.7 Pa`, and surface-shell mean about
`85.9 Pa`.

Mode `4` normalized did not behave like a clean Dirichlet boundary. It behaved
more like an over-strong, spatially nonuniform Robin-like boundary. Median
SPH/FV flux ratios were about `1.63`, `2.26`, and `2.18` for `dp=0.010`,
`0.008`, and `0.0065`; the `dp=0.0065` final ratio reached `-7.27`, indicating
flux reversal.

### C5j MLS Flux Prototype

Mode `5` used constrained radial linear MLS to estimate a normal-gradient
flux and distribute it as a near-surface shell-average correction. The
`dp=0.008` and `dp=0.010` pressure-only runs completed with `code=0`,
`excluded=0`, and `Kplastic=0`.

The center and volume RMSE improved relative to mode `4`, but the solution
remained far from FV. Surface-shell final means were about `311.1 Pa` and
`557.8 Pa` versus the FV `85.9 Pa`. Final center pressures were about
`446.1 Pa` and `579.2 Pa` versus the FV center near `1000 Pa`. Flux ratios
remained high, with final values about `4.10` and `4.03`.

### C5k Radial-Shell Boundary Flux

Mode `6` replaced local flux accumulation with a radial-shell FV boundary flux
correction. The `dp=0.010` case improved center RMSE to `245.05 Pa`, better
than mode `4` and mode `5`, and had a median flux ratio of `1.078`. However,
the final surface-shell mean stayed at `577.06 Pa` versus FV `85.9 Pa`.

The `dp=0.008` case still developed late apparent flux reversal, with final
flux ratio `-14.20` and a final `PorePressRate` maxAbs of `3.13e6 Pa/s`.

### C5l Radial Operator Audit

C5l made no source changes. It showed that the material-only SPH pressure
operator preserves a constant field exactly, but fails near the curved boundary
for radial fields. For `u=r^2`, the interior was acceptable while the
near-boundary p95 absolute error was about `12.24`, `14.06`, and `17.08` across
the existing resolutions, with negative bias. Drained-like radial fields were
worse and did not converge at `dp=0.0065`.

The audit explained why mode `6` could have a reasonable global flux ratio
while the surface shell remained wrong: the outer sink, outer-to-middle
exchange, and interior Laplacian were not one consistent radial diffusion
operator.

### C5m Conservative Shell Exchange

Mode `7` enforced conservative radial FV shell exchange. Its shell
storage/flux residual was reduced to machine precision, about `1e-15`, but the
pressure-only gate still failed. The `dp=0.010` case improved the surface-shell
RMSE while worsening center and volume mean. The `dp=0.008` case did not
improve center, volume, or surface shell, and developed late flux reversal.

This proved that shell bookkeeping alone is not the missing piece.

### C5n Corrected Laplacian

Mode `8` introduced a boundary-aware local quadratic MLS Laplacian. The static
manufactured gate improved strongly. At `dp=0.008`, near-boundary `u=r^2` p95
error dropped from `13.81` to roundoff when the manufactured boundary value was
consistent, and drained-like `R-r` p95 error dropped from `121.32` to `5.23`.

The dynamic pressure-only FV gate failed badly. Final center pressure was
`47.38 Pa` versus FV `999.998 Pa`; final volume mean was `232.26 Pa` versus
FV `615.76 Pa`; final surface-shell mean was `431.67 Pa` versus FV `85.88 Pa`.
The run produced negative pressure, flux reversal, and final `PorePressRate`
maxAbs `9.37e6 Pa/s`.

### C5o Corrected Laplacian Stabilization

C5o added mode-8-only positivity, MLS/material blend, and blend-plus-positivity
limiters. The manufactured gate remained acceptable as a diagnostic. The
pressure-only FV gate still failed.

The best center case was blend `0.25`: final center pressure was `927.58 Pa`
and final `PorePressRate` maxAbs dropped from `9.37e6` to `2.62e6 Pa/s`.
However, final volume mean was `968.38 Pa` versus FV `615.76 Pa`, final
surface-shell mean was `1038.91 Pa` versus FV `85.88 Pa`, negative pressure
still occurred, and every limiter case retained apparent flux reversal.

No C5o compression smoke was run.

## Main Technical Conclusion

The current local boundary and shell-correction routes do not pass the
pressure-only spherical diffusion gate. This includes:

- material-side spherical ghost and quadrature routes;
- boundary-particle prescribed drained states;
- normalized boundary-particle weighting;
- local MLS flux correction;
- radial-shell boundary flux correction;
- conservative multi-shell exchange;
- boundary-aware corrected Laplacian;
- simple local stabilization and blend limiters.

The FV pressure-only spherical diffusion gate is required before a credible
Cryer Figure 7B comparison. Because that gate is still failing, the strict
Cryer route is deferred and C6 must not start.

## What Has Been Proven Useful

The work is not wasted. The following pieces are useful for later benchmarks
or a future redesigned Cryer boundary:

- the linear elastic skeleton switch works and keeps `Kplastic=0` in these
  diagnostic cases;
- CPU flexible confining stress works as a spherical traction candidate;
- the no-elevation hydraulic mode is the right gravity-free pressure equation
  path for Cryer-style diffusion;
- the FV radial diffusion reference and shell diagnostics are valuable
  acceptance gates;
- the Cryer analytical reference script remains available;
- the mode-by-mode boundary diagnostics clarify which simple fixes are not
  sufficient.

## What Remains Unresolved

The unresolved items are fundamental enough to block Figure 7B:

- robust curved drained PR diffusion boundary;
- near-boundary Laplacian consistency during dynamic diffusion;
- pressure-only spherical diffusion gate;
- GPU implementation of the strict curved drained route;
- full Figure 7B validation.

## Decision

The strict Cryer attempt is frozen after C5o. Do not continue local patching of
Cryer boundary operators, do not enter C6, and do not cite the current Cryer
case as a validation figure.

Strict Cryer can be revisited only as a redesigned dynamic drained-boundary
value problem, not as another local limiter, scalar flux correction, or simple
resolution refinement.

## Recommended Next Benchmark

Move to the next benchmark rather than continuing the current strict Cryer
route. The recommended next step is an undrained triaxial baseline because it
tests stress path, pore-pressure response, and constitutive switching without
requiring a spherical drained diffusion boundary.

An external-load 1D full reproduction remains a good consolidation extension,
but it is less direct for stress-path validation. Retrogressive slope work
should wait until the mechanical and constitutive baselines are cleaner.
