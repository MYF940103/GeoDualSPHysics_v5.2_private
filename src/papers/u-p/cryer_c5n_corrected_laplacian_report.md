# C5n Corrected Laplacian Report

## Summary

C5n implemented `CurvedDrainedBoundaryMode=8`, a CPU-only boundary-aware
quadratic MLS Laplacian prototype for the curved drained sphere. The mode keeps
the drained value `p_b=0` for the pressure-only Cryer diffusion gate, avoids
material pressure clamping, and does not count dummy boundary-particle volume.

The manufactured Laplacian gate improved strongly, but the pressure-only FV
diffusion gate failed. Therefore no Cryer compression smoke was run, C6 remains
blocked, and GPU work remains deferred.

## Implementation

Mode `8` is a local quadratic MLS Laplacian recovery. For near-boundary
particles it fits a 10-term quadratic polynomial in local coordinates and
replaces the near-boundary `LapPorePress` by:

```text
nabla^2 p = 2 (a_xx + a_yy + a_zz)
```

The fit includes material neighbors and spherical boundary samples. In the
pressure-only drained gate, the boundary samples use the prescribed Dirichlet
value `p_b=0`. The implementation is CPU-only experimental through
`PorePressureBoundaryOperator=3`; GPU execution still hard-errors because
operator `3` remains CPU-only.

## Manufactured Gate

The static audit reconstructed the committed sphere clouds and compared the
material-only operator with mode `8`.

For `dp=0.008`, near-boundary results were:

| Field | Operator | near-boundary p95 abs error |
|---|---:|---:|
| `u=1` | material-only | `0` |
| `u=r^2` | material-only | `13.81` |
| `u=r^2` | mode 8 with exact boundary values | `~2.6e-14` |
| `u=R-r` | material-only | `121.32` |
| `u=R-r` | mode 8 drained boundary | `5.23` |

The mode-8 static diagnostics had zero fallback for the dp=0.008 cloud:
`848` targets, median condition estimate about `1.86e3`, p95 about `7.13e3`.

This confirms that the quadratic MLS reconstruction can remove the specific
near-boundary polynomial consistency defect found in C5l.

## Pressure-Only Gate

The CPU Release pressure-only diffusion case ran at `dp=0.008`:

- `code=0`;
- `excluded=0`;
- `Kplastic=0`;
- `1213` material particles;
- no compression load and no GPU run.

The gate did not pass:

| Metric | FV / target | mode 8 |
|---|---:|---:|
| final center pressure | `999.998 Pa` | `47.38 Pa` |
| final volume mean | `615.76 Pa` | `232.26 Pa` |
| final surface shell mean | `85.88 Pa` | `431.67 Pa` |
| center RMSE | lower is better | `596.09 Pa` |
| volume RMSE | lower is better | `425.44 Pa` |
| surface shell RMSE | lower is better | `752.41 Pa` |
| median flux ratio | `1` | `-0.00266` |
| final flux ratio | `1` | `-14.53` |
| final `PorePressRate` maxAbs | lower is better | `9.37e6 Pa/s` |

Mode `8` also produced negative pressure during the run. Because the pressure
field became nonphysical and the apparent flux reversed, compression smoke was
skipped.

## Comparison With Previous Modes

At `dp=0.008`, pressure-only RMSEs were:

| Mode | center RMSE | volume RMSE | surface RMSE | median flux ratio |
|---:|---:|---:|---:|---:|
| 4 normalized | `381.52` | `167.67` | `410.71` | `2.264` |
| 5 MLS flux | `344.87` | `136.90` | `475.85` | `2.220` |
| 6 shell flux | `358.80` | `179.64` | `496.74` | `1.907` |
| 7 shell exchange | `386.46` | `212.52` | `498.64` | `1.927` |
| 8 corrected Laplacian | `596.09` | `425.44` | `752.41` | `-0.00266` |

Mode `8` is therefore better as a manufactured consistency diagnostic, but not
better as the dynamic drained diffusion boundary.

## Interpretation

The static and dynamic gates now disagree in an important way:

- The local quadratic fit fixes polynomial Laplacian recovery near the curved
  support when boundary values are consistent with the manufactured field.
- In the actual drained diffusion problem, the same local constrained fit sees
  an initial discontinuity between `u0=1000 Pa` material pressure and `p_b=0`
  boundary samples. Applying that fitted Laplacian directly over the whole
  near-boundary support is too strong and creates oscillatory redistribution.

The remaining blocker is not global flux bookkeeping, and it is not simply
polynomial recovery. It is the coupling between a boundary-constrained local
operator and the explicit PR time update near a discontinuous spherical
Dirichlet boundary.

## Decision

- Mode `8` is implemented.
- The manufactured Laplacian gate passes for polynomial consistency and the
  drained-like radial gap field.
- The pressure-only FV gate fails.
- No compression smoke was run.
- C6 Figure 7B quantitative comparison remains blocked.
- GPU remains deferred.

## Next Source Task

The next task should be a bounded operator-stability prototype, not another
flux-only or shell-only correction. The most useful next step is:

**C5o: boundary-constrained corrected Laplacian stabilization gate**

Recommended scope:

- keep mode `8` as the baseline corrected operator;
- restrict the corrected Laplacian to a thinner boundary layer or blend it with
  the material operator using a consistency-preserving limiter;
- test stability against the same manufactured fields and C5i FV diffusion
  reference;
- explicitly measure whether the limiter prevents negative pressure and flux
  reversal without destroying `u=r^2` and `R-r` near-boundary consistency.

Do not enter C6 until a pressure-only FV gate passes without flux reversal,
strong over-drain, or pressure-rate blow-up.
