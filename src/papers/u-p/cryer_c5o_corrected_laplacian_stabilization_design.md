# C5o Corrected Laplacian Stabilization Design

Date: 2026-05-13

## Scope

C5o is a CPU-only stabilization step for `CurvedDrainedBoundaryMode=8`. It
does not change the PR governing equation, does not modify modes `0` through
`7`, does not clamp material `PorePress`, and does not count dummy boundary
volume. GPU support remains a hard deferred path for the curved drained
operator.

The goal is to keep the C5n manufactured-solution benefit of the boundary-aware
quadratic MLS Laplacian while preventing the pressure-only spherical diffusion
case from over-draining into negative pressure and late apparent flux reversal.

## Why C5n Over-Drained

C5n proved that a local quadratic MLS reconstruction can recover manufactured
radial Laplacians near the sphere when the boundary samples are consistent with
the manufactured field. For `dp=0.008`, the near-boundary `u=r^2` p95 error
fell from about `13.81` to roundoff and the drained-like `R-r` p95 error fell
from about `121.32` to `5.23`.

That static consistency did not transfer to transient pressure-only diffusion.
The dynamic case prescribes `p_b=0` while the initial material field is uniform
`1000 Pa`. The same boundary samples that make the polynomial fit consistent
also impose a very steep local gap in a truncated support. The quadratic fit can
convert this boundary gap into large curvature. During time integration this
creates an aggressive negative pressure-rate layer, then overshoot, negative
pressures, and apparent flux reversal. The C5n pressure-only gate ended with:

- center pressure `47.38 Pa` versus FV `999.998 Pa`;
- volume mean `232.26 Pa` versus FV `615.76 Pa`;
- surface shell mean `431.67 Pa` versus FV `85.88 Pa`;
- final flux ratio `-14.53`;
- negative pressure present;
- final `PorePressRate` maxAbs `9.37e6 Pa/s`.

The failure is therefore not polynomial consistency alone. It is a dynamic
boundary-layer stability problem caused by applying the full boundary-constrained
MLS Laplacian as an explicit pressure diffusion operator.

## Limiter Options

The least invasive stabilization choices are local and diagnostic:

1. Positivity limiter.
   Cap the negative diffusion part of the recovered Laplacian so a pressure-only
   update cannot remove more than `CurvedDrainedLimiterCFL` of the local drained
   pressure gap over the current time-step estimate. The implementation uses
   `LastDt` when available, then `SymplecticDtPre`, then the pore-pressure
   stability limit as a fallback.

2. Blended MLS/material Laplacian.
   Replace the full MLS value by
   `theta * Lap_MLS + (1 - theta) * Lap_material`, using
   `CurvedDrainedLimiterBlend` as `theta`. This tests whether full MLS strength
   is the destabilizing ingredient without changing the interior material
   operator.

3. Optional positivity after blending.
   `CurvedDrainedLimiterPreventNegative=1` applies the positivity cap after the
   selected limiter.

Shell-flux-bounded limiters were not implemented in C5o because C5k/C5m already
showed that global FV-style flux matching can look acceptable while the surface
shell remains wrong. A shell flux cap would also be close to calibration against
the FV reference, which C5o avoids.

## Implemented Parameters

All new parameters default to the old C5n behavior.

| Parameter | Values | Default | Meaning |
|---|---:|---:|---|
| `CurvedDrainedCorrectedLaplacianLimiter` | `0/1/3` | `0` | `0`: off, `1`: positivity limiter, `3`: blended MLS/material Laplacian. |
| `CurvedDrainedLimiterCFL` | `[0,1]` | `0.9` | Fraction of the local pressure gap that the positivity limiter can remove over the pore-pressure timestep estimate. |
| `CurvedDrainedLimiterBlend` | `[0,1]` | `1` | Blend factor `theta` for `theta*Lap_MLS + (1-theta)*Lap_material`. |
| `CurvedDrainedLimiterPreventNegative` | `0/1` | `0` | Apply the positivity cap after the selected mode-8 limiter. |

## Diagnostics

Mode 8 now reports, per pressure-boundary update:

- limiter id and prevent-negative flag;
- limiter timestep, CFL, and blend factor;
- corrected/fallback counts;
- limiter target count;
- blend-limited and positivity-limited counts;
- theta statistics;
- mean/max absolute limiter delta relative to the raw MLS Laplacian;
- max absolute diffusion-rate contribution from the final limited Laplacian.

These are written only to the CPU log. Postprocessing extracts them into
`c5o_limiter_activation_stats.csv`.

## Expected Trade-off

The positivity limiter is designed to preserve static manufactured consistency
unless it activates on a field with negative curvature large enough to violate
the positivity cap. The blend limiter deliberately weakens the exact MLS
operator, so it is expected to degrade manufactured consistency in exchange for
dynamic stability. That trade-off is acceptable only if the pressure-only FV
gate also improves center, volume, surface-shell, flux-ratio, and negative
pressure behavior.
