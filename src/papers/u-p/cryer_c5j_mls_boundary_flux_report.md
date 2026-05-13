# C5j MLS Boundary Flux Report

## Objective

C5j implements an experimental CPU-only MLS / flux-consistent spherical
drained boundary prototype and tests it only with the pressure-only radial
diffusion gate. No GPU run was performed, no Cryer compression run was
performed, and no C6 Figure 7B comparison is claimed.

Artifacts are retained under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5j_MLSBoundaryFlux/`

## Implementation Summary

`CurvedDrainedBoundaryMode=5` was added to the existing
`PorePressureBoundaryOperator=3` curved drained path. It is a hybrid Route-C
prototype:

- constrained radial linear MLS estimates the normal pressure gradient against
  the physical spherical drained surface;
- the boundary value remains prescribed `p_b=0`;
- the integrated MLS normal flux is converted to a shell-average
  `LapPorePress` correction;
- material `PorePress` is never clamped;
- selected dummy boundary particles are not volume-counted;
- CPU diagnostics report target count, sample count, fallback count, condition
  stats, integrated boundary flux, and storage-rate correction.

Mode `5` is not the default. GPU remains unsupported through the existing hard
error for `PorePressureBoundaryOperator=3` / `PorePressureCurvedDrained=1`.

## Pressure-Only Runs

Two CPU Release pressure-only cases were run:

| case | dp | material particles | code | excluded | Kplastic max |
|---|---:|---:|---:|---:|---:|
| mode5 MLS finer | `0.008` | `1213` | `0` | `0` | `0` |
| mode5 MLS coarse | `0.010` | `739` | `0` | `0` | `0` |

The gate reference is the C5i FV radial diffusion solution with
`R=0.05 m`, `u0=1000 Pa`, and `c_v=0.0067957866 m2/s`. At the retained final
time near `0.00603 s`, the FV reference has center pressure `999.998 Pa`,
volume mean `615.7 Pa`, and `0.95R-1.0R` shell mean `85.9 Pa`.

## Gate Metrics

| case | final center | final volume mean | final shell mean | center RMSE | volume RMSE | shell RMSE |
|---|---:|---:|---:|---:|---:|---:|
| FV reference | `999.998` | `615.7` | `85.9` | n/a | n/a | n/a |
| mode 5, dp=0.008 | `446.09` | `356.59` | `311.12` | `344.87` | `136.90` | `475.85` |
| mode 5, dp=0.010 | `579.19` | `550.62` | `557.77` | `253.27` | `54.58` | `573.91` |

Compared with the C5i mode-4 normalized cases, mode `5` improves center and
volume RMSE for both tested dp values, and it removes the late flux reversal
that was present in the C5h `dp=0.0065` mode-4 case. However, the surface shell
is still far too pressurized and its RMSE is worse than mode `4` for both
tested dp values.

## Flux Diagnostics

| case | median flux ratio | final flux ratio | flux reversal | negative pressure | final PorePressRate maxAbs |
|---|---:|---:|---|---|---:|
| mode 4 normalized, dp=0.008 | `2.264` | `2.928` | no | no | `3.26e5 Pa/s` |
| mode 5, dp=0.008 | `2.220` | `4.101` | no | no | `3.80e5 Pa/s` |
| mode 4 normalized, dp=0.010 | `1.631` | `3.727` | no | no | `3.33e5 Pa/s` |
| mode 5, dp=0.010 | `1.494` | `4.029` | no | no | `3.48e5 Pa/s` |

The shell-average correction improves the median flux ratio slightly, but the
late-time flux ratio is still too high, around `4`. The pressure-rate artifact
is not materially lower than mode `4`; it remains the same order of magnitude.

Mode `5` support diagnostics were stable:

| case | targets | average samples | fallback count | condition mean | condition max |
|---|---:|---:|---:|---:|---:|
| dp=0.008 | `962` | `14.79` | `0` | `100.45` | `195.34` |
| dp=0.010 | `592` | `17.51` | `0` | `104.78` | `197.55` |

The failure is therefore not an MLS fallback failure. It is a flux placement
and radial-profile consistency failure.

## Boundary Classification

Mode `5` is not a true Dirichlet drained boundary yet. It is also no longer the
same over-strong nonuniform pair-count boundary as mode `4`, because selected
boundary particle volumes are not counted and flux reversal is removed in the
tested cases.

The best current classification is:

```text
mode 5 = over-strong shell-flux boundary with poor radial profile consistency
```

It drains storage too aggressively at late time while leaving the near-surface
shell much too high relative to the FV surface shell.

## Compression Smoke Decision

The pressure-only gate did not pass. The surface shell pressure, final flux
ratio, and center decay remain far from the FV reference. Per C5j criteria, no
Cryer compression smoke was run.

## Conclusions

1. Mode `5` was implemented and runs successfully on CPU.
2. It is a shell-averaged MLS normal-flux correction, not a full
   MLS-corrected Laplacian.
3. The prescribed drained boundary value remains `p_b=0`.
4. Material pore pressure is not clamped.
5. Pressure-only diffusion is not sufficiently closer to FV than mode `4`.
6. Median flux ratio improves slightly, but final flux ratio remains too high.
7. Flux reversal is absent in the tested mode-5 cases.
8. The pressure-rate artifact is not reduced enough.
9. Surface shell pressure remains the main failure.
10. Center pressure still decays much too early.
11. No compression smoke was run because the pressure-only gate failed.
12. C6 remains blocked.
13. Further dp/geometry refinement is not recommended until the pressure-only
    gate is fixed.
14. GPU remains deferred.

## Recommended Next Source Task

The next task should not be a broad dp study. It should be a narrower
boundary-flux implementation step:

```text
C5k: radial finite-volume matched boundary source or per-shell flux limiter
```

The specific blocker is that the current MLS flux is integrated but not
radially profile-consistent. The next prototype should couple the boundary
flux to a radial shell balance or FV-matched transfer law so that volume decay,
surface-shell pressure, and center pressure are all constrained together before
returning to Cryer compression.
