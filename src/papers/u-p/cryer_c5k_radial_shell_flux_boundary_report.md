# C5k Radial-Shell Flux Boundary Report

## Objective

C5k implements `CurvedDrainedBoundaryMode=6`, a CPU-only radial-shell /
finite-volume spherical drained flux prototype, and tests it only with the
pressure-only radial diffusion gate. No GPU run was performed, no Cryer
compression smoke was run, and no C6 Figure 7B comparison is claimed.

Artifacts are retained under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5k_RadialShellFluxBoundary/`

## Implementation Summary

Mode `6` is different from C5j mode `5`. Mode `5` used local constrained radial
MLS gradients and then formed a shell-average correction. Mode `6` starts from
the radial-shell conservation statement directly:

```text
d/dt int_V u dV = -4*pi*R^2*q_R
q_R = D * (u_shell - u_b) / (R - r_shell)
u_b = 0 Pa
```

The implementation:

- keeps the prescribed drained value `p_b=0`;
- uses shell-averaged pressure and radius near the physical sphere surface;
- converts the integrated flux to a `LapPorePress` correction over the outer
  material shell;
- leaves material `PorePress` unclamped;
- does not volume-count dummy boundary particles;
- prints shell populations, shell pressure, boundary flux, storage correction,
  and flux residual diagnostics.

It does not modify the PR governing equation, flexible confining stress,
constitutive model, hydraulic elevation convention, or modes `0` to `5`.
GPU remains unsupported through the existing curved drained boundary hard
error.

## Pressure-Only Runs

Two CPU Release pressure-only runs were executed:

| case | dp | material particles | surface roughness std | code | excluded | Kplastic max |
|---|---:|---:|---:|---:|---:|---:|
| mode 6 radial-shell finer | `0.008` | `1213` | `0.003033` | `0` | `0` | `0` |
| mode 6 radial-shell coarse | `0.010` | `739` | `0.003577` | `0` | `0` | `0` |

The reference remains the C5i FV radial diffusion solution with `R=0.05 m`,
`u0=1000 Pa`, and `c_v=0.0067957866 m2/s`. At `t ~= 0.00603 s`, the FV
reference has center pressure `999.998 Pa`, volume mean `615.7 Pa`, and
`0.95R-1.0R` shell mean `85.9 Pa`.

## Gate Metrics

| case | final center | final volume mean | final shell mean | shell p95 abs |
|---|---:|---:|---:|---:|
| FV reference | `999.998` | `615.7` | `85.9` | n/a |
| mode 6, dp=0.008 | `842.79` | `806.68` | `873.84` | `1176.36` |
| mode 6, dp=0.010 | `631.41` | `591.04` | `577.06` | `611.56` |

| case | center RMSE | volume RMSE | shell RMSE | median flux ratio | final flux ratio |
|---|---:|---:|---:|---:|---:|
| mode 4 normalized, dp=0.008 | `381.52` | `167.67` | `410.71` | `2.264` | n/a |
| mode 5 MLS, dp=0.008 | `344.87` | `136.90` | `475.85` | `2.220` | n/a |
| mode 6 radial-shell, dp=0.008 | `358.80` | `179.64` | `496.74` | `1.907` | `-14.200` |
| mode 4 normalized, dp=0.010 | `292.17` | `74.79` | `525.67` | `1.631` | n/a |
| mode 5 MLS, dp=0.010 | `253.27` | `54.58` | `573.91` | `1.494` | n/a |
| mode 6 radial-shell, dp=0.010 | `245.05` | `63.83` | `581.08` | `1.078` | `0.784` |

The coarse `dp=0.010` run shows useful local improvements: center RMSE improves
over modes `4` and `5`, volume RMSE improves over mode `4`, the median flux
ratio is close to `1`, and `PorePressRate` maxAbs drops to `1.52e5 Pa/s`.

The finer `dp=0.008` run does not improve. It has a late apparent storage-flux
reversal, final flux ratio `-14.20`, surface shell rebound, and a
`PorePressRate` artifact of `3.13e6 Pa/s`.

## Surface-Shell Failure

The main gate failure remains the surface shell. FV predicts a final shell mean
near `85.9 Pa`. Mode `6` ends at:

- `873.84 Pa` for `dp=0.008`;
- `577.06 Pa` for `dp=0.010`.

The shell pressure does not approach the Dirichlet radial profile. For
`dp=0.008`, the outer shell drains initially but rebounds late, producing the
negative apparent storage flux ratio. This means the radial-shell source term
alone is not enough to control the coupled SPH radial profile and storage
balance.

## Flux Diagnostics

The source-side integrated mode-6 boundary flux remains positive because it is
computed from the outer shell mean pressure and the prescribed `u_b=0`. The
postprocessed apparent flux ratio is computed from the volume-storage decay.
Those two diagnostics diverge in the failed `dp=0.008` run: the applied
boundary sink is positive, but the retained material volume mean rebounds at
late time.

That is the most important C5k finding. A shell-conservative boundary source
can still be overwhelmed by radial redistribution, pressure-rate artifacts, or
inconsistent interaction with the interior SPH Laplacian.

## Compression Smoke Decision

The pressure-only gate did not clearly pass:

- `dp=0.008` has flux reversal and a large pressure-rate spike;
- `dp=0.010` improves flux ratio and center pressure but leaves the surface
  shell far too pressurized;
- surface-shell RMSE is not better than the retained alternatives.

Therefore no Cryer compression smoke was run.

## Conclusions

1. `CurvedDrainedBoundaryMode=6` is implemented.
2. Mode `6` is a radial-shell / FV conservation flux correction, not local MLS
   and not an arbitrary FV curve fit.
3. The drained value remains `p_b=0`.
4. Material pressure is not clamped.
5. Pressure-only diffusion is not globally closer to FV than modes `4` and
   `5`.
6. The `dp=0.010` flux ratio improves materially, but `dp=0.008` fails with a
   late flux reversal.
7. No negative pressure over-drain was detected in the retained frames.
8. `PorePressRate` improves for `dp=0.010` but becomes much worse for
   `dp=0.008`.
9. Surface-shell pressure remains the primary blocker.
10. No compression smoke was run because the pressure-only gate failed.
11. C6 Figure 7B comparison remains blocked.
12. GPU remains deferred.

## Next Blocker

The remaining blocker is no longer just boundary flux strength. C5k shows that
forcing a radial-shell integrated flux does not automatically give the correct
radial profile. The next source task should couple the boundary flux with the
near-boundary SPH Laplacian/interior redistribution, for example by a
conservative radial reconstruction that updates both the outer shell sink and
the adjacent shell exchange, while retaining the pressure-only FV gate as the
acceptance test.
