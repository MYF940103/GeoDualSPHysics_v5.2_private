# C5o Corrected Laplacian Stabilization Report

Date: 2026-05-13

## Result

C5o implemented mode-8-only CPU limiter controls and ran the pressure-only
spherical diffusion gate at `dp=0.008`. All C5o simulations completed with
`code=0`, `excluded=0`, and `Kplastic=0`. No GPU run was performed.

The pressure-only FV gate did not pass. No Cryer compression smoke was run.
C6 Figure 7B quantitative comparison remains blocked.

## Implemented Limiters

Mode 8 remains the C5n boundary-aware quadratic MLS Laplacian:

```text
p(xi) ~= a0 + a1 xi_x + a2 xi_y + a3 xi_z
       + a4 xi_x^2 + a5 xi_y^2 + a6 xi_z^2
       + a7 xi_x xi_y + a8 xi_x xi_z + a9 xi_y xi_z

nabla^2 p = 2(a4 + a5 + a6)
```

C5o adds:

- `CurvedDrainedCorrectedLaplacianLimiter=1`: positivity cap on negative
  diffusion-rate strength;
- `CurvedDrainedCorrectedLaplacianLimiter=3`: blended
  `theta*Lap_MLS + (1-theta)*Lap_material`;
- `CurvedDrainedLimiterPreventNegative=1`: optional positivity cap after a
  blend.

Defaults keep the old C5n behavior (`limiter=0`, blend `1`, prevent negative
`0`). The limiter acts on the recovered `LapPorePress` only. It does not clamp
material pressure and does not count boundary-particle volume.

## Manufactured Gate

The exact mode-8 manufactured consistency is preserved when the limiter is off.
The positivity limiter leaves `u=r^2` unchanged in the static gate but alters
the drained-like `R-r` case because it caps strong negative curvature.

For `dp=0.008`, near-boundary p95 Laplacian error:

| Field | Operator | p95 error |
|---|---:|---:|
| `u=r^2` | material only | `13.81` |
| `u=r^2` | mode 8 exact boundary | `2.6e-14` |
| `u=r^2` | positivity | `2.6e-14` |
| `u=r^2` | blend 0.25 | `10.36` |
| `u=r^2` | blend 0.50 | `6.91` |
| `u=R-r` | material only | `121.32` |
| `u=R-r` | mode 8 exact boundary | `5.23` |
| `u=R-r` | positivity | `39.04` |
| `u=R-r` | blend 0.25 | `89.69` |
| `u=R-r` | blend 0.50 | `58.07` |

The manufactured gate is acceptable as a diagnostic regression, but the blend
limiter clearly trades consistency for stability.

## Pressure-Only Gate

FV reference at final time is approximately:

- center `999.998 Pa`;
- volume mean `615.76 Pa`;
- surface shell mean `85.88 Pa`.

Final C5o values:

| Case | Center | Volume mean | Surface shell | Center RMSE | Volume RMSE | Surface RMSE |
|---|---:|---:|---:|---:|---:|---:|
| mode 8 off | `47.38` | `232.26` | `431.67` | `596.09` | `425.44` | `752.41` |
| positivity | `280.79` | `469.85` | `702.59` | `539.59` | `388.12` | `761.42` |
| blend 0.25 | `927.58` | `968.38` | `1038.91` | `104.83` | `238.85` | `760.00` |
| blend 0.50 | `756.15` | `844.21` | `976.10` | `233.56` | `227.98` | `723.92` |
| blend 0.50 + positivity | `759.42` | `847.13` | `979.24` | `233.06` | `228.36` | `724.55` |

The blend cases greatly improve center pressure versus raw mode 8, especially
blend `0.25`, and reduce final `PorePressRate` maxAbs. They also make the
surface shell much worse: the final surface shell remains around
`976-1039 Pa` versus FV `85.88 Pa`. That is not a drained spherical diffusion
solution.

## Flux, Negative Pressure, and Artifacts

| Case | Median flux ratio | Final flux ratio | Flux reversal | Max negative count | Min pressure | Final PorePressRate maxAbs |
|---|---:|---:|---|---:|---:|---:|
| mode 8 off | `-0.003` | `-14.53` | yes | old C5n | old C5n | `9.37e6` |
| positivity | `-0.003` | `-21.30` | yes | `863` | `-4915.36` | `9.74e6` |
| blend 0.25 | `-0.266` | `-7.52` | yes | `24` | `-225.50` | `2.62e6` |
| blend 0.50 | `-0.574` | `-13.03` | yes | `120` | `-1694.80` | `4.99e6` |
| blend 0.50 + positivity | `-0.574` | `-13.12` | yes | `120` | `-1682.95` | `4.99e6` |

The best diagnostic case is blend `0.25`: it reduces the pressure-rate artifact
from `9.37e6` to `2.62e6 Pa/s` and limits the negative-pressure episode to 24
particles with minimum pressure about `-225 Pa`. It still has apparent flux
reversal and a surface shell that is far too high. The positivity limiter does
activate during the run, but it does not stop the failure because the
instability is not purely a single local negative-rate overshoot.

## Interpretation

C5o confirms that the C5n failure is not fixed by a simple local limiter.
Reducing MLS strength can protect the center pressure and lower rate spikes,
but the dynamic boundary layer remains inconsistent: the outer shell does not
diffuse toward the drained FV profile and the apparent global flux still
reverses.

The remaining blocker is the corrected Laplacian formulation itself as a
dynamic operator near a drained curved surface. The strict Cryer route should
not proceed by tuning blend factors. A calibrated blend could make one metric
look better while failing the surface-shell and flux criteria.

## Answers

1. Mode 8 stabilization was implemented.
2. Implemented limiters: positivity, fixed MLS/material blend, optional
   positivity after blend.
3. Negative pressure was not eliminated. Blend `0.25` strongly reduced it.
4. `PorePressRate` artifact was reduced by blend `0.25`, but not enough.
5. The pressure-only FV gate did not pass.
6. The best limiter was blend `0.25` by center RMSE and rate artifact, but it
   failed surface shell and flux criteria.
7. Manufactured consistency is preserved by positivity for `u=r^2`, but blend
   modes intentionally degrade it.
8. Compression smoke was not run because the pressure-only gate failed.
9. C6 is still blocked.
10. The next decision should be whether to stop the strict Cryer route in the
    current SPH boundary-operator family or redesign the drained boundary as a
    true dynamic boundary value problem rather than another local/shell limiter.
    GPU remains deferred.
