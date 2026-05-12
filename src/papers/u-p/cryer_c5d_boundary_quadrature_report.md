# C5d Boundary Quadrature Report

Date: 2026-05-12

## Objective

C5d tested a principled CPU-only refinement of the Cryer curved drained
pore-pressure boundary. The new experimental submode is
`CurvedDrainedBoundaryMode=3`, a multi-sample spherical Dirichlet boundary
quadrature for `PorePressureBoundaryOperator=3`.

The task did not run GPU, did not perform a Poisson-ratio sweep, and does not
claim Figure 7B reproduction.

## Implementation Summary

Mode `3` constructs five virtual drained samples near the local spherical
projection of each near-surface material particle. Each sample has drained
Dirichlet value `excess=0` (`p_w=0` under `HydraulicElevationSource=0`) and
contributes directly to `LapPorePress` and `LapZ` before `PorePressRate`.

This differs from:

- mode `0`: one first-order drained ghost;
- mode `1`: one strengthened image ghost;
- mode `2`: diagnostic material surface clamp after the pressure update.

Mode `3` never overwrites material pore pressure and is therefore a boundary
quadrature experiment, not a clamp.

## Test Matrix

All C5d tests were CPU Release only.

| Case | Purpose | Result |
|---|---|---|
| old ghost | C5/C5c compression baseline, mode `0` | `code=0`, `excluded=0` |
| strong ghost | mode `1` compression comparison | `code=0`, `excluded=0` |
| quadrature | new mode `3` compression comparison | `code=0`, `excluded=0` |
| surface clamp | diagnostic upper-bound comparison, mode `2` | `code=0`, `excluded=0` |
| diffusion old/strong/quadrature/clamp | pressure-only uniform-excess diffusion checks | all `code=0`, `excluded=0` |

`Kplastic` remained zero in all cases.

## Compression Results

At the final retained frame (`t=0.006032 s`) for the `r>0.85R` material shell:

| Case | Center peak `p_w/p0` | Final center `p_w/p0` | Surface p95 abs [Pa] | Surface max abs [Pa] |
|---|---:|---:|---:|---:|
| old ghost | 7.672 | 2.923 | 218.47 | 263.15 |
| strong ghost | 7.663 | 2.819 | 212.58 | 258.29 |
| quadrature | 7.657 | 2.796 | 208.90 | 252.39 |
| diagnostic clamp | 2.218 | 1.571 | 0.00 | 0.00 |

Relative to the old ghost, the new quadrature reduced:

- center peak by only `0.20%`;
- final center pressure by `4.37%`;
- final surface p95 residual by `4.38%`;
- final surface maximum residual by `4.09%`.

The result is stable but not a large enough correction to unlock quantitative
Cryer comparison.

## Pressure-Only Diffusion

For the uniform-excess pressure-only diffusion smoke, the final center and
surface residuals were:

| Case | Final center excess [Pa] | Final surface p95 abs [Pa] | Final velocity max [m/s] |
|---|---:|---:|---:|
| old ghost | 968.65 | 967.28 | 4.73e-05 |
| strong ghost | 938.40 | 935.82 | 9.32e-05 |
| quadrature | 946.83 | 946.35 | 1.91e-04 |
| diagnostic clamp | -380.72 | 0.00 | 7.36e-03 |

The quadrature increases boundary contribution and pressure-rate activity, but
it does not outperform the strengthened ghost in this short diffusion window.
It remains far better behaved than the diagnostic clamp, which strongly
over-drains and produces large pressure-rate/velocity artifacts.

## Pressure-Rate Artifacts

Mode `3` did not produce clamp-like artifacts in the compression smoke:

- final compression `PorePressRate` maxAbs was `2.67e5 Pa/s`, comparable to the
  old and strengthened ghost cases;
- final velocity max was `1.05e-3 m/s`, comparable to the old case;
- `Kplastic=0`.

In the pressure-only diffusion smoke, mode `3` had higher pressure-rate and
velocity than old/strong ghost. This is a useful warning that the current
quadrature weight is not yet a final calibrated boundary rule.

## Interpretation

C5d confirms three things:

1. The C5c surface residual is a real material-surface coupling problem, not a
   ghost-value diagnostic artifact.
2. A simple local five-point Dirichlet quadrature is stable and avoids the
   diagnostic clamp pathology.
3. The improvement is marginal. The near-surface material layer is still not
   strongly enough coupled to the drained boundary for Figure 7B quantitative
   comparison.

## Recommendation

Do not proceed to C6 quantitative Cryer comparison yet.

The next step should be either:

- a more complete boundary method, such as MLS/boundary-particle-aware
  quadrature with better surface measure normalization; or
- modest geometry/dp refinement only after the boundary rule is made less
  weak.

GPU remains deferred. Strict Cryer reproduction is still incomplete.
