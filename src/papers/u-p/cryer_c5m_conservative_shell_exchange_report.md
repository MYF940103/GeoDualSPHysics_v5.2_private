# C5m Conservative Shell Exchange Report

## Scope

C5m implemented `CurvedDrainedBoundaryMode=7` as a CPU-only experimental
conservative multi-shell radial exchange prototype for
`PorePressureBoundaryOperator=3`. No GPU case was run, no Cryer compression
case was run, and C6 Figure 7B comparison remains out of scope.

The pressure-only gate is retained under:

```text
examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5m_ConservativeShellExchange/
```

## Numerical Form

Mode `7` uses a radial FV conservation target:

```text
dS_k/dt = F_{k-1/2} - F_{k+1/2}
F_{k+1/2} = -D A (u_{k+1}-u_k) / dr
F_R = D 4*pi*R^2 (u_outer - 0) / (R-r_outer)
```

It was run with `CurvedDrainedShellCorrectionMode=1`, meaning a
shell-average correction:

```text
LapPorePress_i += (target_shell_rate - current_shell_average_rate) / D
```

This is based on radial FV conservation. It does not clamp material pore
pressure, does not use dummy boundary volume, and leaves the PR governing
equation update form unchanged.

## Pressure-Only Gate

Both CPU Release pressure-only cases completed:

| case | code | excluded | Kplastic max | final time |
|---|---:|---:|---:|---:|
| `dp=0.008` | 0 | 0 | 0 | 0.006032 s |
| `dp=0.010` | 0 | 0 | 0 | 0.006032 s |

FV reference at the final frame is approximately:

- center pressure: `999.998 Pa`;
- volume mean: `615.727 Pa`;
- surface shell mean: `85.867 Pa`.

Mode `7` results:

| case | final center | final volume mean | final surface shell mean | median flux ratio | final flux ratio | PorePressRate maxAbs |
|---|---:|---:|---:|---:|---:|---:|
| `dp=0.008` | `861.47 Pa` | `858.48 Pa` | `969.08 Pa` | `1.927` | `-19.36` | `4.48e6 Pa/s` |
| `dp=0.010` | `512.37 Pa` | `438.09 Pa` | `381.88 Pa` | `1.929` | `2.31` | `3.01e5 Pa/s` |

## Conservation Diagnostics

The intended shell storage balance was enforced internally:

- maximum logged `storage + boundary flux` residual was about `7.1e-15` for
  `dp=0.008`;
- maximum logged residual was about `3.6e-15` for `dp=0.010`.

So the shell correction machinery does what it was designed to do at the
discrete shell-storage level.

## Gate Decision

The pressure-only gate did not pass.

Compared with modes `4`, `5`, and `6`:

- `dp=0.010` improves surface shell RMSE relative to modes `4`, `5`, and `6`,
  but worsens center and volume-mean RMSE and does not improve flux ratio;
- `dp=0.008` does not improve center, volume, or surface metrics and develops
  a late apparent flux reversal;
- `dp=0.008` has a strong pressure-rate artifact (`4.48e6 Pa/s`), worse than
  mode `6`;
- neither case develops negative pressure in the saved pressure field.

No compression smoke was run because the pressure-only gate failed.

## Interpretation

Mode `7` proves that shell-average FV conservation can be imposed, but that
alone is not enough. The operator can conserve shell storage while still
producing the wrong radial diffusion dynamics. The remaining blocker is not
only boundary flux strength or shell bookkeeping. It is now more likely a
combination of:

- coarse/rough spherical shell populations;
- excessive correction concentrated in the outer and adjacent shells;
- incompatibility between shell-average FV replacement/correction and the
  local SPH pressure-feedback/Shepard update path;
- missing true corrected SPH Laplacian consistency near the curved boundary.

## Readiness

- C6 is still blocked.
- GPU remains deferred.
- Further simple dp refinement is not recommended.
- The next source task should not be another scalar flux calibration. The
  recommended next step is a true corrected near-boundary SPH Laplacian /
  consistency operator, with the C5m shell balance retained as a diagnostic
  gate rather than as the main production route.
