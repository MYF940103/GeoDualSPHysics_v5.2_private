# C5i Spherical Diffusion Flux Calibration Report

## Objective

C5i pauses Cryer compression refinement and uses pressure-only spherical
diffusion as the acceptance gate for the drained spherical boundary. No source
files were modified, no GPU run was performed, no new Cryer compression case
was run, and no C6 Figure 7B comparison is claimed.

Artifacts are retained under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5i_SphericalDiffusionFluxCalibration/`

The untracked `C5i_Dp005FullTimeLongRun/` directory was found during recovery,
but it is a separate dp-refinement/long-run artifact and was not used or
modified.

## FV Radial Reference

The new script `scripts/spherical_radial_diffusion_reference.py` implements a
1D finite-volume radial solver for:

```text
u_t = c_v / r^2 * d/dr(r^2 du/dr)
du/dr = 0 at r=0
u = 0 at r=R
u(r,0) = 1000 Pa
```

The reference parameters are read from the C5h pressure-only XML:

| quantity | value |
|---|---:|
| radius `R` | `0.05 m` |
| initial pressure `u0` | `1000 Pa` |
| porosity | `0.3` |
| hydraulic conductivity | `1e-5 m/s` |
| water bulk modulus | `2e6 Pa` |
| water density | `1000 kg/m3` |
| hydraulic gravity magnitude | `9.81 m/s2` |
| derived `c_v` | `0.0067957866 m2/s` |

At the final retained time near `0.00603 s`, the FV reference gives:

| metric | FV value |
|---|---:|
| center pressure | `999.998 Pa` |
| volume mean pressure | `615.7 Pa` |
| `0.95R-1.0R` shell mean | `85.9 Pa` |
| `0.95R-1.0R` shell p95 | `165.1 Pa` |

This is a useful gate because true radial diffusion drains the specimen volume
while the center stays almost unchanged during this short window.

## SPH vs Reference

Mode 4 normalized pressure-only diffusion is not close to the FV reference:

| case | final center | final volume mean | final shell mean | center RMSE | volume RMSE | shell RMSE |
|---|---:|---:|---:|---:|---:|---:|
| dp=0.010 | `529.96 Pa` | `492.92 Pa` | `509.70 Pa` | `292.17 Pa` | `74.79 Pa` | `525.67 Pa` |
| dp=0.008 | `468.25 Pa` | `367.19 Pa` | `318.94 Pa` | `381.52 Pa` | `167.67 Pa` | `410.71 Pa` |
| dp=0.0065 | `746.40 Pa` | `524.07 Pa` | `425.24 Pa` | `430.65 Pa` | `253.56 Pa` | `325.82 Pa` |

The main discrepancy is spatial structure:

- the SPH center pressure decays far too early relative to true spherical
  diffusion;
- the SPH near-surface shell remains much too high relative to the drained
  Dirichlet reference;
- the volume mean can still drain faster than reference, so the error is not a
  simple weak boundary condition.

This combination means the operator is redistributing/removing pressure in a
non-radial, non-flux-consistent way.

## Boundary Type

The apparent flux ratio was computed from volume-mean pressure decay:

```text
SPH apparent boundary flux / FV boundary flux
```

The t=0 point is not used for classification because the Dirichlet initial
condition has a boundary discontinuity. Median ratios below are for `t>0`.

| case | median flux ratio | final flux ratio | effective type |
|---|---:|---:|---|
| mode 3 shell, dp=0.010 | `0.217` | `0.058` | weak Robin |
| mode 4 raw, dp=0.010 | `3.429` | `3.592` | over-strong nonuniform Robin |
| mode 4 normalized, dp=0.010 | `1.631` | `3.727` | over-strong nonuniform Robin |
| mode 4 capped diagnostic, dp=0.010 | `0.115` | `-0.766` | nonuniform / flux-reversal Robin |
| mode 4 normalized, dp=0.008 | `2.264` | `2.928` | over-strong nonuniform Robin |
| mode 4 normalized, dp=0.0065 | `2.180` | `-7.275` | nonuniform / flux-reversal Robin |

Mode 3 is clearly under-drained. Raw mode 4 is over-strong and crosses into
negative pressure. Normalized mode 4 removes the strong raw negative pressure,
but it does not become a true Dirichlet boundary. It behaves like an
over-strong, nonuniform Robin-like boundary: apparent storage decay is too
large, while the surface shell is still not held close to zero.

## Why dp=0.0065 Did Not Improve

The higher-resolution sphere adds particles, but not boundary quality:

| metric | dp=0.010 | dp=0.008 | dp=0.0065 |
|---|---:|---:|---:|
| material particles | `739` | `1213` | `2601` |
| selected boundary particles | `2418` | `3794` | `5802` |
| material-boundary pairs | `194490` | `315386` | `650052` |
| surface roughness std | `0.00358` | `0.00303` | `0.00365` |
| max surface radius abs error | `0.00641` | `0.00692` | `0.00738` |
| final pressure-rate maxAbs | `3.33e5 Pa/s` | `3.26e5 Pa/s` | `1.55e6 Pa/s` |

The `dp=0.0065` case has more boundary pairs but a rougher generated surface,
a larger maximum radius error, a much larger pressure-rate artifact, and a
late-time apparent flux reversal. Sphere roughness does not explain all of the
error, but it explains why simply adding particles can worsen the boundary
operator: the selected boundary cloud and material shell do not form a
monotone-quality spherical quadrature.

## Interpretation

C5i confirms that the current strict Cryer blocker is the drained spherical
boundary flux, not only center extraction or sphere resolution.

The desired true Dirichlet behavior would have:

- surface shell pressure close to the FV shell values;
- volume-average decay close to the FV decay;
- a flux ratio near `1`;
- no sign reversal or negative pressure artifact.

The current normalized mode 4 has none of these as a stable set. It drains the
global stored pressure too aggressively at many frames, but it leaves the
near-surface shell too pressurized. This is the signature of a nonuniform,
non-flux-consistent boundary contribution rather than a scalar weighting error.

## Decisions

1. The radial diffusion FV reference is established.
2. Pressure-only SPH differs most in spatial consistency: center drains too
   early, surface shell remains too high, and apparent volume flux is often too
   large.
3. Mode 4 normalized is best described as over-strong nonuniform Robin-like,
   with flux reversal at `dp=0.0065`.
4. The normalized mode 4 flux ratio is roughly `1.6-2.3` in median over the
   retained frames; the `dp=0.0065` final frame reverses sign.
5. The `dp=0.0065` degradation is consistent with worse generated surface
   quality and boundary-selection/pair-count amplification.
6. MLS / flux-consistent boundary development is needed before any C6
   comparison.
7. Further dp refinement is not recommended until the pressure-only diffusion
   gate passes.
8. C6 Figure 7B quantitative comparison remains premature.
9. GPU remains deferred because the strict Cryer path still depends on
   CPU-only boundary/loading/hydraulic modes.

